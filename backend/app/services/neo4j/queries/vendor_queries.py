from typing import Any
from uuid import UUID

from app.services.neo4j.driver import neo4j_manager
from app.services.neo4j.repository import Neo4jUnavailableError, run_read


def query_graph_risk_discovery(*, organization_id: UUID) -> dict[str, Any]:
    """Deterministic Neo4j Cypher queries identifying connected risk indicators."""
    if not neo4j_manager.is_enabled() or not neo4j_manager.verify_connectivity()[0]:
        return {
            "source": "unavailable",
            "degraded": True,
            "disclaimer": "Risk indicators only — not proof of fraud.",
            "patterns": [],
        }

    org_id_str = str(organization_id)
    patterns: list[dict[str, Any]] = []
    try:
        # 1. Vendors with >= 2 exceptions across POs
        rep_vendors = run_read(
            """
            MATCH (v:Vendor {organization_id: $org_id})-[:ISSUED]->(p:PurchaseOrder)
                  -[:EVALUATED_BY]->(:ReconciliationRun)-[:GENERATED]->(ex:Exception)
            WITH v, count(DISTINCT ex) AS exc_count, collect(DISTINCT p.po_number)[0..5] AS pos
            WHERE exc_count >= 2
            RETURN v.source_id AS vendor_id, v.label AS vendor_name, exc_count, pos
            ORDER BY exc_count DESC
            LIMIT 10
            """,
            {"org_id": org_id_str},
        )
        for row in rep_vendors:
            patterns.append(
                {
                    "pattern_type": "REPEATED_VENDOR_EXCEPTIONS",
                    "title": f"{row['vendor_name']} linked to {row['exc_count']} exceptions",
                    "vendor_id": row["vendor_id"],
                    "evidence": f"POs: {', '.join(row['pos'])}",
                    "limitation": "Graph count reflects reconciled exceptions only; requires human review.",
                }
            )

        # 2. Multiple invoices billed against a single PO
        multi_inv = run_read(
            """
            MATCH (i:Invoice {organization_id: $org_id})-[:BILLS_AGAINST]->(p:PurchaseOrder)
            WITH p, count(DISTINCT i) AS inv_cnt, collect(DISTINCT i.invoice_number)[0..5] AS invs
            WHERE inv_cnt >= 2
            RETURN p.source_id AS po_id, p.po_number AS po_number, inv_cnt, invs
            ORDER BY inv_cnt DESC
            LIMIT 10
            """,
            {"org_id": org_id_str},
        )
        for row in multi_inv:
            patterns.append(
                {
                    "pattern_type": "MULTIPLE_INVOICES_PER_PO",
                    "title": f"{row['po_number']} has {row['inv_cnt']} linked invoices",
                    "po_id": row["po_id"],
                    "evidence": f"Invoices: {', '.join(row['invs'])}",
                    "limitation": "May represent valid split billing or duplicate submission.",
                }
            )

        # 3. Incomplete delivery chains (PO with Invoice but no GoodsReceipt)
        missing_grn = run_read(
            """
            MATCH (i:Invoice {organization_id: $org_id})-[:BILLS_AGAINST]->(p:PurchaseOrder)
            WHERE NOT (p)-[:HAS_RECEIPT]->(:GoodsReceipt)
            RETURN p.source_id AS po_id, p.po_number AS po_number, i.invoice_number AS inv_num
            LIMIT 10
            """,
            {"org_id": org_id_str},
        )
        for row in missing_grn:
            patterns.append(
                {
                    "pattern_type": "INCOMPLETE_DELIVERY_CHAIN",
                    "title": f"{row['po_number']} billed ({row['inv_num']}) without Goods Receipt",
                    "po_id": row["po_id"],
                    "evidence": f"PO {row['po_number']} -> Invoice {row['inv_num']} (0 GRNs)",
                    "limitation": "Warehouse receipt may still be pending entry.",
                }
            )

        return {
            "source": "neo4j",
            "degraded": False,
            "disclaimer": "Risk indicators only — not proof of fraud.",
            "patterns": patterns,
        }
    except Neo4jUnavailableError:
        return {
            "source": "unavailable",
            "degraded": True,
            "disclaimer": "Risk indicators only — not proof of fraud.",
            "patterns": [],
        }
