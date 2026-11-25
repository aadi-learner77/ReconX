from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.domain import (
    Approval,
    ExceptionCase,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    Vendor,
)
from app.repositories.base import OrgScopedRepository


def build_transaction_evidence_graph(
    db: Session, *, organization_id: UUID, transaction_id: UUID
) -> dict[str, Any]:
    """Build Financial Evidence Graph nodes & edges from PostgreSQL (Decision D2)."""
    po = OrgScopedRepository(db, PurchaseOrder, organization_id).get_by_id(transaction_id)
    inv_repo = OrgScopedRepository(db, Invoice, organization_id)
    grn_repo = OrgScopedRepository(db, GoodsReceipt, organization_id)

    if po is not None:
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(po.vendor_id)
        grns = list(db.scalars(grn_repo.base_query().where(GoodsReceipt.po_id == po.id)).all())
        invoices = list(db.scalars(inv_repo.base_query().where(Invoice.po_id == po.id)).all())
    else:
        single_inv = inv_repo.get_by_id(transaction_id)
        if not single_inv:
            return {"nodes": [], "edges": [], "source": "postgresql_relational"}
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(single_inv.vendor_id)
        grns = []
        invoices = [single_inv]

    excs = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, organization_id)
            .base_query()
            .where(ExceptionCase.transaction_id == transaction_id)
        ).all()
    )
    approvals = list(
        db.scalars(
            OrgScopedRepository(db, Approval, organization_id)
            .base_query()
            .where(Approval.transaction_id == transaction_id)
        ).all()
    )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    if vendor:
        nodes.append(
            {
                "id": f"vendor:{vendor.id}",
                "type": "Vendor",
                "label": vendor.legal_name,
                "data": {"tax_identifier": vendor.tax_identifier, "status": vendor.status},
            }
        )

    if po:
        nodes.append(
            {
                "id": f"po:{po.id}",
                "type": "PurchaseOrder",
                "label": po.po_number,
                "data": {
                    "total": str(po.total_amount),
                    "currency": po.currency,
                    "status": po.status,
                },
            }
        )
        if vendor:
            edges.append(
                {
                    "id": f"e-v-po-{po.id}",
                    "source": f"vendor:{vendor.id}",
                    "target": f"po:{po.id}",
                    "label": "ISSUED",
                }
            )
        for ln in po.lines:
            prod_id = f"product:{ln.item_code or ln.id}"
            nodes.append(
                {
                    "id": prod_id,
                    "type": "Product",
                    "label": f"{ln.item_code or 'ITEM'} ({ln.quantity} {ln.uom})",
                    "data": {"description": ln.description, "unit_price": str(ln.unit_price)},
                }
            )
            edges.append(
                {
                    "id": f"e-po-prod-{ln.id}",
                    "source": f"po:{po.id}",
                    "target": prod_id,
                    "label": "CONTAINS",
                }
            )

    for g in grns:
        nodes.append(
            {
                "id": f"grn:{g.id}",
                "type": "GoodsReceipt",
                "label": g.grn_number,
                "data": {"status": g.status, "received_at": g.received_at.isoformat()},
            }
        )
        if po:
            edges.append(
                {
                    "id": f"e-grn-po-{g.id}",
                    "source": f"grn:{g.id}",
                    "target": f"po:{po.id}",
                    "label": "RECEIVED_AGAINST",
                }
            )

    for inv in invoices:
        nodes.append(
            {
                "id": f"invoice:{inv.id}",
                "type": "Invoice",
                "label": inv.invoice_number,
                "data": {
                    "total": str(inv.total_amount),
                    "currency": inv.currency,
                    "status": inv.status,
                },
            }
        )
        if po:
            edges.append(
                {
                    "id": f"e-inv-po-{inv.id}",
                    "source": f"invoice:{inv.id}",
                    "target": f"po:{po.id}",
                    "label": "BILLED_AGAINST",
                }
            )
        elif vendor:
            edges.append(
                {
                    "id": f"e-v-inv-{inv.id}",
                    "source": f"vendor:{vendor.id}",
                    "target": f"invoice:{inv.id}",
                    "label": "REFERENCES",
                }
            )

    for e in excs:
        nodes.append(
            {
                "id": f"exception:{e.id}",
                "type": "Exception",
                "label": f"{e.type} ({e.status})",
                "data": {"severity": e.severity, "rule_id": e.rule_id, "summary": e.summary},
            }
        )
        anchor = f"po:{po.id}" if po else (f"invoice:{invoices[0].id}" if invoices else "")
        if anchor:
            edges.append(
                {
                    "id": f"e-exc-{e.id}",
                    "source": anchor,
                    "target": f"exception:{e.id}",
                    "label": "FLAGGED_BY",
                }
            )

    for ap in approvals:
        nodes.append(
            {
                "id": f"approval:{ap.id}",
                "type": "Approval",
                "label": f"{ap.decision} ({ap.amount_evaluated})",
                "data": {"rationale": ap.rationale, "decided_at": ap.decided_at.isoformat()},
            }
        )
        target = f"exception:{ap.case_id}" if ap.case_id else f"po:{ap.transaction_id}"
        edges.append(
            {
                "id": f"e-app-{ap.id}",
                "source": target,
                "target": f"approval:{ap.id}",
                "label": "APPROVED_BY",
            }
        )

    return {"nodes": nodes, "edges": edges, "source": "postgresql_relational"}
