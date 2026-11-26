from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.domain import ExceptionCase, Investigation
from app.repositories.base import OrgScopedRepository
from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.repository import Neo4jUnavailableError, run_read


def query_agent_investigations(db: Session, *, organization_id: UUID) -> dict[str, Any]:
    """List persisted investigations from Neo4j AgentRun nodes with PostgreSQL fallback."""
    if neo4j_manager.is_enabled() and neo4j_manager.verify_connectivity()[0]:
        try:
            rows = run_read(
                """
                MATCH (ar:AgentRun {organization_id: $org_id})
                OPTIONAL MATCH (ar)-[:INVESTIGATES]->(ex:Exception {organization_id: $org_id})
                RETURN ar, ex.type AS case_type, ex.severity AS case_severity
                ORDER BY ar.created_at DESC
                LIMIT 25
                """,
                {"org_id": str(organization_id)},
            )
            items = []
            for r in rows:
                props = dict(r["ar"])
                items.append(
                    {
                        "investigation_id": props.get("investigation_id"),
                        "case_id": props.get("case_id"),
                        "case_type": r.get("case_type") or "EXCEPTION",
                        "case_severity": r.get("case_severity") or "MEDIUM",
                        "model_provider": props.get("actual_provider", props.get("model_provider")),
                        "model_name": props.get("model_name"),
                        "status": props.get("status"),
                        "fallback_used": props.get("fallback_used", False),
                        "latency_ms": props.get("latency_ms", 0.0),
                        "created_at": props.get("created_at"),
                    }
                )
            return {"items": items, "source": "neo4j", "degraded": False}
        except Neo4jUnavailableError:
            pass

    invs = list(
        db.scalars(
            OrgScopedRepository(db, Investigation, organization_id)
            .base_query()
            .order_by(desc(Investigation.created_at))
            .limit(25)
        ).all()
    )
    items = []
    for i in invs:
        out = i.structured_output_json or {}
        c = db.get(ExceptionCase, i.case_id)
        items.append(
            {
                "investigation_id": str(i.id),
                "case_id": str(i.case_id),
                "case_type": c.type if c else "EXCEPTION",
                "case_severity": c.severity if c else "MEDIUM",
                "model_provider": out.get("actual_provider", i.model_provider),
                "model_name": i.model_name,
                "status": i.status,
                "fallback_used": out.get("fallback_used", False),
                "latency_ms": out.get("latency_ms", 0.0),
                "created_at": i.created_at.isoformat(),
            }
        )
    return {"items": items, "source": "postgresql_fallback", "degraded": neo4j_manager.is_enabled()}


def query_agent_execution_graph(
    db: Session,
    *,
    organization_id: UUID,
    investigation_id: UUID,
) -> dict[str, Any]:
    """Retrieve real AgentRun -> AgentStageExecution -> ToolCall & EvidenceReference graph."""
    if neo4j_manager.is_enabled() and neo4j_manager.verify_connectivity()[0]:
        try:
            rows = run_read(
                """
                MATCH (ar:AgentRun {organization_id: $org_id, investigation_id: $inv_id})
                OPTIONAL MATCH (ar)-[r1:INVESTIGATES]->(ex:Exception {organization_id: $org_id})
                OPTIONAL MATCH (ar)-[r2:PRODUCED_INVESTIGATION]->(ig:Investigation {organization_id: $org_id})
                OPTIONAL MATCH (ar)-[r3:EXECUTED_STAGE]->(st:AgentStageExecution {organization_id: $org_id})
                OPTIONAL MATCH (st)-[r4:CALLED_TOOL]->(tc:ToolCall {organization_id: $org_id})
                OPTIONAL MATCH (st)-[r5:REFERENCED]->(er:EvidenceReference {organization_id: $org_id})
                OPTIONAL MATCH (st)-[r6:NEXT_STAGE]->(st2:AgentStageExecution {organization_id: $org_id})
                RETURN ar, ex, ig, st, tc, er, st2, r1, r2, r3, r4, r5, r6
                """,
                {"org_id": str(organization_id), "inv_id": str(investigation_id)},
            )
            if not rows:
                from app.services.neo4j.sync_service import sync_investigation_to_neo4j

                if sync_investigation_to_neo4j(
                    db, organization_id=organization_id, investigation_id=investigation_id
                ):
                    rows = run_read(
                        """
                        MATCH (ar:AgentRun {organization_id: $org_id, investigation_id: $inv_id})
                        OPTIONAL MATCH (ar)-[r1:INVESTIGATES]->(ex:Exception {organization_id: $org_id})
                        OPTIONAL MATCH (ar)-[r2:PRODUCED_INVESTIGATION]->(ig:Investigation {organization_id: $org_id})
                        OPTIONAL MATCH (ar)-[r3:EXECUTED_STAGE]->(st:AgentStageExecution {organization_id: $org_id})
                        OPTIONAL MATCH (st)-[r4:CALLED_TOOL]->(tc:ToolCall {organization_id: $org_id})
                        OPTIONAL MATCH (st)-[r5:REFERENCED]->(er:EvidenceReference {organization_id: $org_id})
                        OPTIONAL MATCH (st)-[r6:NEXT_STAGE]->(st2:AgentStageExecution {organization_id: $org_id})
                        RETURN ar, ex, ig, st, tc, er, st2, r1, r2, r3, r4, r5, r6
                        """,
                        {"org_id": str(organization_id), "inv_id": str(investigation_id)},
                    )

            nodes_map: dict[str, dict[str, Any]] = {}
            edges_map: dict[str, dict[str, Any]] = {}
            for rec in rows:
                for val in rec.values():
                    if val is None:
                        continue
                    if hasattr(val, "labels"):
                        p = dict(val)
                        gk = p.get("graph_key", "")
                        nodes_map[gk] = {
                            "id": gk,
                            "type": p.get("entity_type", "AgentNode"),
                            "label": p.get("label", ""),
                            "data": {
                                k: v
                                for k, v in p.items()
                                if k not in ("graph_key", "organization_id", "entity_type", "label")
                            },
                        }
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
            if nodes_map:
                return {
                    "investigation_id": str(investigation_id),
                    "nodes": list(nodes_map.values()),
                    "edges": list(edges_map.values()),
                    "source": "neo4j",
                    "degraded": False,
                }
        except Neo4jUnavailableError:
            pass

    return {
        "investigation_id": str(investigation_id),
        "nodes": [],
        "edges": [],
        "source": "postgresql_fallback",
        "degraded": neo4j_manager.is_enabled(),
    }


def query_cross_investigation_analytics(*, organization_id: UUID) -> dict[str, Any]:
    """Query Neo4j for cross-investigation vendor patterns, shared evidence, and stage health."""
    if not neo4j_manager.is_enabled() or not neo4j_manager.verify_connectivity()[0]:
        return {
            "source": "unavailable",
            "degraded": True,
            "vendor_investigations": [],
            "shared_evidence": [],
            "stage_stats": [],
        }

    org_id_str = str(organization_id)
    try:
        vendor_invs = run_read(
            """
            MATCH (v:Vendor {organization_id: $org_id})-[:ISSUED]->(:PurchaseOrder)
                  -[:EVALUATED_BY]->(:ReconciliationRun)-[:GENERATED]->(ex:Exception)
                  -[:INVESTIGATED_BY]->(ig:Investigation)
            RETURN v.source_id AS vendor_id, v.label AS vendor_name,
                   count(DISTINCT ig) AS investigation_count,
                   collect(DISTINCT ex.type)[0..5] AS exception_types
            ORDER BY investigation_count DESC
            LIMIT 10
            """,
            {"org_id": org_id_str},
        )
        shared_ev = run_read(
            """
            MATCH (ig:Investigation {organization_id: $org_id})-[:CITES]->(er:EvidenceReference)
            WITH er, count(DISTINCT ig) AS cite_count
            WHERE cite_count >= 1
            RETURN er.source_type AS source_type, er.label AS label,
                   er.source_record_id AS record_id, cite_count
            ORDER BY cite_count DESC
            LIMIT 10
            """,
            {"org_id": org_id_str},
        )
        stage_stats = run_read(
            """
            MATCH (st:AgentStageExecution {organization_id: $org_id})
            RETURN st.agent_name AS agent_name,
                   count(st) AS total_runs,
                   sum(CASE WHEN st.status = 'SUCCEEDED' THEN 1 ELSE 0 END) AS succeeded,
                   sum(CASE WHEN st.status = 'FAILED' THEN 1 ELSE 0 END) AS failed
            ORDER BY total_runs DESC
            """,
            {"org_id": org_id_str},
        )
        return {
            "source": "neo4j",
            "degraded": False,
            "vendor_investigations": vendor_invs,
            "shared_evidence": shared_ev,
            "stage_stats": stage_stats,
        }
    except Neo4jUnavailableError:
        return {
            "source": "unavailable",
            "degraded": True,
            "vendor_investigations": [],
            "shared_evidence": [],
            "stage_stats": [],
        }
