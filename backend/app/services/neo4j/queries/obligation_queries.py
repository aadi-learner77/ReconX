from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.graph.builder import (
    build_transaction_evidence_graph,
    build_transaction_obligation_graph,
)
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.repository import Neo4jUnavailableError, run_read


def _neo4j_node_to_ui(node: Any) -> dict[str, Any]:
    props = dict(node)
    return {
        "id": props.get("graph_key") or f"{props.get('entity_type')}:{props.get('source_id')}",
        "source_id": props.get("source_id", ""),
        "type": props.get("entity_type", "Record"),
        "label": props.get("label", props.get("source_id", "")),
        "data": {
            k: v
            for k, v in props.items()
            if k not in ("graph_key", "organization_id", "entity_type", "label")
        },
    }


def query_obligation_graph(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
    view: str = "overview",
) -> dict[str, Any]:
    """Retrieve Neo4j-backed Obligation / Evidence / Vendor / Fulfilment graph with safe fallback."""
    settings = get_settings()
    pg_ob = build_transaction_obligation_graph(
        db, organization_id=organization_id, transaction_id=transaction_id
    )

    if (
        not settings.feature_neo4j_obligation_graph
        or not neo4j_manager.is_enabled()
        or not neo4j_manager.verify_connectivity()[0]
    ):
        base = (
            build_transaction_evidence_graph(
                db, organization_id=organization_id, transaction_id=transaction_id
            )
            if view == "evidence"
            else pg_ob
        )
        return {
            **base,
            "summary": pg_ob.get("summary", {}),
            "has_payment_records": False,
            "view": view,
            "source": "postgresql_relational_fallback",
            "degraded": neo4j_manager.is_enabled(),
        }

    org_id_str = str(organization_id)
    tx_id_str = str(transaction_id)
    try:
        if view == "evidence":
            cypher = """
            MATCH (p:PurchaseOrder {organization_id: $org_id, source_id: $tx_id})
            OPTIONAL MATCH (d:Document {organization_id: $org_id})-[r1:EVIDENCES]->(p)
            OPTIONAL MATCH (p)-[r2:EVALUATED_BY]->(rr:ReconciliationRun {organization_id: $org_id})
            OPTIONAL MATCH (rr)-[r3:GENERATED]->(ex:Exception {organization_id: $org_id})
            OPTIONAL MATCH (ex)-[r4:INVESTIGATED_BY]->(ig:Investigation {organization_id: $org_id})
            OPTIONAL MATCH (ap:Approval {organization_id: $org_id})-[r5:DECIDES_ON]->(ex)
            OPTIONAL MATCH (pe:PolicyEvaluation {organization_id: $org_id})-[r6:TRIGGERED]->(ex)
            OPTIONAL MATCH (pe)-[r7:EVALUATED_USING]->(pv:PolicyVersion {organization_id: $org_id})
            RETURN p, d, rr, ex, ig, ap, pe, pv, r1, r2, r3, r4, r5, r6, r7
            """
        elif view == "vendor":
            cypher = """
            MATCH (p:PurchaseOrder {organization_id: $org_id, source_id: $tx_id})
            OPTIONAL MATCH (v:Vendor {organization_id: $org_id})-[r0:ISSUED]->(p)
            OPTIONAL MATCH (v)-[r1:ISSUED]->(other_po:PurchaseOrder {organization_id: $org_id})
            OPTIONAL MATCH (other_po)-[r2:EVALUATED_BY]->(rr:ReconciliationRun {organization_id: $org_id})
            OPTIONAL MATCH (rr)-[r3:GENERATED]->(ex:Exception {organization_id: $org_id})
            OPTIONAL MATCH (ex)-[r4:HAS_RISK_SIGNAL]->(rs:RiskSignal {organization_id: $org_id})
            OPTIONAL MATCH (ex)-[r5:INVESTIGATED_BY]->(ig:Investigation {organization_id: $org_id})
            RETURN p, v, other_po, rr, ex, rs, ig, r0, r1, r2, r3, r4, r5
            LIMIT 40
            """
        elif view == "fulfilment":
            cypher = """
            MATCH (p:PurchaseOrder {organization_id: $org_id, source_id: $tx_id})
            OPTIONAL MATCH (p)-[r1:CONTAINS]->(pl:POLine {organization_id: $org_id})
            OPTIONAL MATCH (p)-[r2:HAS_RECEIPT]->(grn:GoodsReceipt {organization_id: $org_id})
            OPTIONAL MATCH (grn)-[r3:CONTAINS]->(gl:GRNLine {organization_id: $org_id})
            OPTIONAL MATCH (gl)-[r4:FULFILLS]->(pl)
            OPTIONAL MATCH (inv:Invoice {organization_id: $org_id})-[r5:BILLS_AGAINST]->(p)
            OPTIONAL MATCH (inv)-[r6:CONTAINS]->(il:InvoiceLine {organization_id: $org_id})
            OPTIONAL MATCH (il)-[r7:CLAIMS_FOR]->(pl)
            RETURN p, pl, grn, gl, inv, il, r1, r2, r3, r4, r5, r6, r7
            """
        else:
            cypher = """
            MATCH (p:PurchaseOrder {organization_id: $org_id, source_id: $tx_id})
            OPTIONAL MATCH (v:Vendor {organization_id: $org_id})-[r0:ISSUED]->(p)
            OPTIONAL MATCH (p)-[r1:CONTAINS]->(pl:POLine {organization_id: $org_id})
            OPTIONAL MATCH (p)-[r2:HAS_RECEIPT]->(grn:GoodsReceipt {organization_id: $org_id})
            OPTIONAL MATCH (inv:Invoice {organization_id: $org_id})-[r3:BILLS_AGAINST]->(p)
            OPTIONAL MATCH (p)-[r4:EVALUATED_BY]->(rr:ReconciliationRun {organization_id: $org_id})
            OPTIONAL MATCH (rr)-[r5:GENERATED]->(ex:Exception {organization_id: $org_id})
            OPTIONAL MATCH (ex)-[r6:INVESTIGATED_BY]->(ig:Investigation {organization_id: $org_id})
            OPTIONAL MATCH (ap:Approval {organization_id: $org_id})-[r7:DECIDES_ON]->(ex)
            RETURN p, v, pl, grn, inv, rr, ex, ig, ap, r0, r1, r2, r3, r4, r5, r6, r7
            """

        records = run_read(cypher, {"org_id": org_id_str, "tx_id": tx_id_str})
        if not records:
            # Auto-sync once on cache miss if Neo4j is online
            from app.services.neo4j.sync_service import sync_transaction_to_neo4j

            if sync_transaction_to_neo4j(
                db, organization_id=organization_id, transaction_id=transaction_id
            ):
                records = run_read(cypher, {"org_id": org_id_str, "tx_id": tx_id_str})

        nodes_map: dict[str, dict[str, Any]] = {}
        edges_map: dict[str, dict[str, Any]] = {}
        for rec in records:
            for val in rec.values():
                if val is None:
                    continue
                if hasattr(val, "labels"):
                    nd = _neo4j_node_to_ui(val)
                    nodes_map[nd["id"]] = nd
                elif hasattr(val, "type") and hasattr(val, "start_node"):
                    s_gk = dict(val.start_node).get("graph_key")
                    t_gk = dict(val.end_node).get("graph_key")
                    if s_gk and t_gk:
                        eid = f"{s_gk}-{val.type}-{t_gk}"
                        props = dict(val)
                        edges_map[eid] = {
                            "id": eid,
                            "source": s_gk,
                            "target": t_gk,
                            "label": val.type,
                            "verified": props.get("verified", True),
                            "method": props.get("method", "relational_fk"),
                        }

        if not nodes_map:
            return {
                **pg_ob,
                "view": view,
                "source": "postgresql_relational_fallback",
                "degraded": False,
            }

        return {
            "nodes": list(nodes_map.values()),
            "edges": list(edges_map.values()),
            "summary": pg_ob.get("summary", {}),
            "has_payment_records": False,
            "view": view,
            "source": "neo4j",
            "degraded": False,
        }
    except Neo4jUnavailableError:
        return {
            **pg_ob,
            "view": view,
            "source": "postgresql_relational_fallback",
            "degraded": True,
        }


def query_vendor_network(
    db: Session,
    *,
    organization_id: UUID,
    vendor_id: UUID,
) -> dict[str, Any]:
    """Query Neo4j for a supplier's connected POs, GRNs, Invoices, Exceptions, and Investigations."""
    if not neo4j_manager.is_enabled() or not neo4j_manager.verify_connectivity()[0]:
        return {"nodes": [], "edges": [], "source": "unavailable", "degraded": True}

    records = run_read(
        """
        MATCH (v:Vendor {organization_id: $org_id, source_id: $vid})
        OPTIONAL MATCH (v)-[r1:ISSUED]->(p:PurchaseOrder {organization_id: $org_id})
        OPTIONAL MATCH (p)-[r2:HAS_RECEIPT]->(g:GoodsReceipt {organization_id: $org_id})
        OPTIONAL MATCH (i:Invoice {organization_id: $org_id})-[r3:BILLS_AGAINST]->(p)
        OPTIONAL MATCH (p)-[r4:EVALUATED_BY]->(rr:ReconciliationRun {organization_id: $org_id})
        OPTIONAL MATCH (rr)-[r5:GENERATED]->(ex:Exception {organization_id: $org_id})
        OPTIONAL MATCH (ex)-[r6:INVESTIGATED_BY]->(ig:Investigation {organization_id: $org_id})
        OPTIONAL MATCH (ex)-[r7:HAS_RISK_SIGNAL]->(rs:RiskSignal {organization_id: $org_id})
        RETURN v, p, g, i, rr, ex, ig, rs, r1, r2, r3, r4, r5, r6, r7
        LIMIT 80
        """,
        {"org_id": str(organization_id), "vid": str(vendor_id)},
    )
    nodes_map: dict[str, dict[str, Any]] = {}
    edges_map: dict[str, dict[str, Any]] = {}
    for rec in records:
        for val in rec.values():
            if val is None:
                continue
            if hasattr(val, "labels"):
                nd = _neo4j_node_to_ui(val)
                nodes_map[nd["id"]] = nd
            elif hasattr(val, "type") and hasattr(val, "start_node"):
                s_gk = dict(val.start_node).get("graph_key")
                t_gk = dict(val.end_node).get("graph_key")
                if s_gk and t_gk:
                    eid = f"{s_gk}-{val.type}-{t_gk}"
                    edges_map[eid] = {
                        "id": eid,
                        "source": s_gk,
                        "target": t_gk,
                        "label": val.type,
                    }
    return {
        "nodes": list(nodes_map.values()),
        "edges": list(edges_map.values()),
        "source": "neo4j",
        "degraded": False,
    }


def query_relationship_path(
    *,
    organization_id: UUID,
    source_graph_key: str,
    target_graph_key: str,
) -> dict[str, Any]:
    """Find shortest valid Neo4j relationship path between two org-scoped nodes."""
    if not neo4j_manager.is_enabled() or not neo4j_manager.verify_connectivity()[0]:
        return {
            "path_found": False,
            "source": "unavailable",
            "degraded": True,
            "nodes": [],
            "edges": [],
            "steps": [],
            "message": "Neo4j is unavailable; path traversal requires active graph connection.",
        }

    records = run_read(
        """
        MATCH (a {organization_id: $org_id, graph_key: $src}),
              (b {organization_id: $org_id, graph_key: $dst}),
              p = shortestPath((a)-[*..8]-(b))
        WHERE ALL(n IN nodes(p) WHERE n.organization_id = $org_id)
        RETURN nodes(p) AS path_nodes, relationships(p) AS path_rels
        LIMIT 1
        """,
        {
            "org_id": str(organization_id),
            "src": source_graph_key,
            "dst": target_graph_key,
        },
    )
    if not records:
        return {
            "path_found": False,
            "source": "neo4j",
            "degraded": False,
            "nodes": [],
            "edges": [],
            "steps": [],
            "message": "No valid path exists between the selected records within 8 hops.",
        }

    rec = records[0]
    p_nodes = [_neo4j_node_to_ui(n) for n in rec["path_nodes"]]
    p_edges = []
    steps = []
    for rel in rec["path_rels"]:
        s_props = dict(rel.start_node)
        e_props = dict(rel.end_node)
        r_props = dict(rel)
        verified = bool(r_props.get("verified", True))
        eid = f"{s_props.get('graph_key')}-{rel.type}-{e_props.get('graph_key')}"
        p_edges.append(
            {
                "id": eid,
                "source": s_props.get("graph_key"),
                "target": e_props.get("graph_key"),
                "label": rel.type,
                "verified": verified,
            }
        )
        steps.append(
            {
                "from_label": s_props.get("label", s_props.get("source_id", "")),
                "from_type": s_props.get("entity_type", ""),
                "from_source_id": s_props.get("source_id", ""),
                "relationship": rel.type,
                "to_label": e_props.get("label", e_props.get("source_id", "")),
                "to_type": e_props.get("entity_type", ""),
                "to_source_id": e_props.get("source_id", ""),
                "verified": verified,
                "method": r_props.get("method", "authoritative_fk"),
            }
        )

    return {
        "path_found": True,
        "source": "neo4j",
        "degraded": False,
        "nodes": p_nodes,
        "edges": p_edges,
        "steps": steps,
    }


def search_obligation_graph(
    *,
    organization_id: UUID,
    q: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not neo4j_manager.is_enabled() or not neo4j_manager.verify_connectivity()[0]:
        return []
    records = run_read(
        """
        MATCH (n {organization_id: $org_id})
        WHERE n.entity_type IN ['Vendor', 'PurchaseOrder', 'GoodsReceipt', 'Invoice', 'Exception']
          AND toLower(coalesce(n.label, '')) CONTAINS toLower($q)
        RETURN n LIMIT $lim
        """,
        {"org_id": str(organization_id), "q": q.strip(), "lim": limit},
    )
    return [_neo4j_node_to_ui(r["n"]) for r in records]
