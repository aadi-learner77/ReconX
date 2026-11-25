from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.domain import (
    Approval,
    ExceptionCase,
    GoodsReceipt,
    Investigation,
    Invoice,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    Vendor,
)
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event


def build_transaction_evidence_graph(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
    include_history: bool = True,
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
    risks = list(
        db.scalars(
            OrgScopedRepository(db, RiskSignal, organization_id)
            .base_query()
            .where(RiskSignal.transaction_id == transaction_id)
        ).all()
    )
    exc_ids = [e.id for e in excs]
    investigations = (
        list(
            db.scalars(
                OrgScopedRepository(db, Investigation, organization_id)
                .base_query()
                .where(Investigation.case_id.in_(exc_ids))
            ).all()
        )
        if exc_ids
        else []
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
        if inv.duplicate_of_invoice_id:
            edges.append(
                {
                    "id": f"e-inv-dup-{inv.id}",
                    "source": f"invoice:{inv.id}",
                    "target": f"invoice:{inv.duplicate_of_invoice_id}",
                    "label": "DUPLICATE_OF",
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

    for inv_case in investigations:
        nodes.append(
            {
                "id": f"investigation:{inv_case.id}",
                "type": "Investigation",
                "label": f"Investigation ({inv_case.status})",
                "data": {
                    "model_provider": inv_case.model_provider,
                    "confidence": str(inv_case.confidence),
                },
            }
        )
        edges.append(
            {
                "id": f"e-invst-{inv_case.id}",
                "source": f"exception:{inv_case.case_id}",
                "target": f"investigation:{inv_case.id}",
                "label": "INVESTIGATED_BY",
            }
        )

    for sig in risks:
        nodes.append(
            {
                "id": f"risk:{sig.id}",
                "type": "RiskSignal",
                "label": f"{sig.signal_type} ({sig.severity})",
                "data": {"score": str(sig.score), "model_version": sig.model_version},
            }
        )
        anchor = f"po:{po.id}" if po else (f"invoice:{invoices[0].id}" if invoices else "")
        if anchor:
            edges.append(
                {
                    "id": f"e-risk-{sig.id}",
                    "source": anchor,
                    "target": f"risk:{sig.id}",
                    "label": "FLAGGED_RISK",
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

    if include_history and vendor:
        prior_pos = list(
            db.scalars(
                OrgScopedRepository(db, PurchaseOrder, organization_id)
                .base_query()
                .where(
                    PurchaseOrder.vendor_id == vendor.id,
                    PurchaseOrder.id != transaction_id,
                )
                .order_by(desc(PurchaseOrder.issue_date))
                .limit(5)
            ).all()
        )
        for hp in prior_pos:
            nodes.append(
                {
                    "id": f"po:{hp.id}",
                    "type": "HistoricalPO",
                    "label": hp.po_number,
                    "data": {
                        "total": str(hp.total_amount),
                        "currency": hp.currency,
                        "status": hp.status,
                    },
                }
            )
            edges.append(
                {
                    "id": f"e-hist-po-{hp.id}",
                    "source": f"vendor:{vendor.id}",
                    "target": f"po:{hp.id}",
                    "label": "HISTORICAL_PO",
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "include_history": include_history,
        "source": "postgresql_relational",
    }


def rebuild_transaction_evidence_graph(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
    actor_id: str,
) -> dict[str, Any]:
    """Deterministically rebuild and audit the relational evidence graph projection."""
    graph = build_transaction_evidence_graph(
        db,
        organization_id=organization_id,
        transaction_id=transaction_id,
        include_history=True,
    )
    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=actor_id,
        action="GRAPH_REBUILT",
        entity_type="evidence_graph",
        entity_id=str(transaction_id),
        after={"node_count": len(graph["nodes"]), "edge_count": len(graph["edges"])},
    )
    db.commit()
    return graph


def build_transaction_obligation_graph(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
) -> dict[str, Any]:
    """Build Financial Obligation Graph from PostgreSQL using Decimal arithmetic."""
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
            return {
                "nodes": [],
                "edges": [],
                "summary": {},
                "has_payment_records": False,
                "source": "postgresql_relational",
            }
        vendor = OrgScopedRepository(db, Vendor, organization_id).get_by_id(single_inv.vendor_id)
        grns = []
        invoices = [single_inv]

    runs = list(
        db.scalars(
            OrgScopedRepository(db, ReconciliationRun, organization_id)
            .base_query()
            .where(ReconciliationRun.transaction_id == transaction_id)
            .order_by(desc(ReconciliationRun.completed_at))
            .limit(1)
        ).all()
    )
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
    exc_ids = [e.id for e in excs]
    investigations = (
        list(
            db.scalars(
                OrgScopedRepository(db, Investigation, organization_id)
                .base_query()
                .where(Investigation.case_id.in_(exc_ids))
            ).all()
        )
        if exc_ids
        else []
    )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    if vendor:
        nodes.append(
            {
                "id": f"vendor:{vendor.id}",
                "type": "Supplier",
                "label": vendor.legal_name,
                "data": {"tax_identifier": vendor.tax_identifier, "status": vendor.status},
            }
        )

    total_ordered = Decimal("0")
    total_accepted = Decimal("0")
    total_invoiced = Decimal("0")
    total_po_amount = po.total_amount if po else Decimal("0")

    if po:
        nodes.append(
            {
                "id": f"po:{po.id}",
                "type": "PurchaseOrder",
                "label": po.po_number,
                "data": {
                    "po_number": po.po_number,
                    "total": str(po.total_amount),
                    "currency": po.currency,
                    "status": po.status,
                    "issue_date": str(po.issue_date),
                },
            }
        )
        if vendor:
            edges.append(
                {
                    "id": f"e-v-po-{po.id}",
                    "source": f"vendor:{vendor.id}",
                    "target": f"po:{po.id}",
                    "label": "RECEIVES_ORDER",
                }
            )

        for ln in po.lines:
            ordered = Decimal(str(ln.quantity))
            total_ordered += ordered
            acc_for_line = Decimal("0")
            for g in grns:
                for gl in g.lines:
                    if gl.po_line_id == ln.id or (gl.item_code and gl.item_code == ln.item_code):
                        acc_for_line += Decimal(str(gl.accepted_qty))
            total_accepted += acc_for_line
            outstanding = max(Decimal("0"), ordered - acc_for_line)
            if acc_for_line <= 0:
                ob_status = "OPEN"
            elif outstanding > 0:
                ob_status = "PARTIALLY_FULFILLED"
            else:
                ob_status = "FULFILLED"

            po_line_nid = f"po_line:{ln.id}"
            ob_nid = f"obligation:{ln.id}"
            nodes.append(
                {
                    "id": po_line_nid,
                    "type": "POLine",
                    "label": f"{ln.item_code or 'ITEM'} ({ordered} {ln.uom})",
                    "data": {
                        "item_code": ln.item_code,
                        "ordered_qty": str(ordered),
                        "unit_price": str(ln.unit_price),
                        "uom": ln.uom,
                    },
                }
            )
            edges.append(
                {
                    "id": f"e-po-ln-{ln.id}",
                    "source": f"po:{po.id}",
                    "target": po_line_nid,
                    "label": "CONTAINS",
                }
            )
            nodes.append(
                {
                    "id": ob_nid,
                    "type": "DeliveryObligation",
                    "label": f"Obligation: {acc_for_line}/{ordered} ({ob_status})",
                    "data": {
                        "ordered_qty": str(ordered),
                        "accepted_qty": str(acc_for_line),
                        "outstanding_qty": str(outstanding),
                        "status": ob_status,
                    },
                }
            )
            edges.append(
                {
                    "id": f"e-ln-ob-{ln.id}",
                    "source": po_line_nid,
                    "target": ob_nid,
                    "label": "CREATES",
                }
            )

    for g in grns:
        grn_nid = f"grn:{g.id}"
        nodes.append(
            {
                "id": grn_nid,
                "type": "GoodsReceipt",
                "label": g.grn_number,
                "data": {"status": g.status, "received_at": g.received_at.isoformat()},
            }
        )
        for gl in g.lines:
            gl_nid = f"grn_line:{gl.id}"
            nodes.append(
                {
                    "id": gl_nid,
                    "type": "GRNLine",
                    "label": f"{gl.item_code or 'GRN'} (Acc: {gl.accepted_qty})",
                    "data": {
                        "accepted_qty": str(gl.accepted_qty),
                        "rejected_qty": str(gl.rejected_qty),
                    },
                }
            )
            edges.append(
                {
                    "id": f"e-grn-gl-{gl.id}",
                    "source": grn_nid,
                    "target": gl_nid,
                    "label": "RECORDS",
                }
            )
            if gl.po_line_id:
                edges.append(
                    {
                        "id": f"e-gl-ob-{gl.id}",
                        "source": gl_nid,
                        "target": f"obligation:{gl.po_line_id}",
                        "label": "FULFILLS",
                    }
                )

    today = date.today()
    for inv in invoices:
        inv_nid = f"invoice:{inv.id}"
        claim_status = inv.status
        if any(a.decision == "APPROVE" for a in approvals):
            claim_status = "APPROVED"
        elif any(a.decision == "REJECT" for a in approvals):
            claim_status = "REJECTED"
        elif excs and claim_status not in ("APPROVED", "REJECTED"):
            claim_status = "EXCEPTION"
        elif runs and runs[0].outcome == "MATCHED":
            claim_status = "MATCHED"

        nodes.append(
            {
                "id": inv_nid,
                "type": "Invoice",
                "label": f"{inv.invoice_number} ({claim_status})",
                "data": {
                    "invoice_number": inv.invoice_number,
                    "total": str(inv.total_amount),
                    "currency": inv.currency,
                    "due_date": str(inv.due_date),
                    "overdue": inv.due_date < today,
                    "claim_status": claim_status,
                },
            }
        )
        for il in inv.lines:
            total_invoiced += Decimal(str(il.quantity))
            il_nid = f"inv_line:{il.id}"
            nodes.append(
                {
                    "id": il_nid,
                    "type": "InvoiceLine",
                    "label": f"{il.item_code or 'INV'} ({il.quantity} @ {il.unit_price})",
                    "data": {"quantity": str(il.quantity), "unit_price": str(il.unit_price)},
                }
            )
            edges.append(
                {
                    "id": f"e-inv-il-{il.id}",
                    "source": inv_nid,
                    "target": il_nid,
                    "label": "CONTAINS",
                }
            )
            if il.po_line_id:
                edges.append(
                    {
                        "id": f"e-il-pol-{il.id}",
                        "source": il_nid,
                        "target": f"po_line:{il.po_line_id}",
                        "label": "BILLS_AGAINST",
                    }
                )

    for run in runs:
        run_nid = f"recon:{run.id}"
        nodes.append(
            {
                "id": run_nid,
                "type": "ReconciliationRun",
                "label": f"Reconciliation ({run.outcome})",
                "data": {"outcome": run.outcome, "completed_at": run.completed_at.isoformat()},
            }
        )
        if po:
            edges.append(
                {
                    "id": f"e-run-po-{run.id}",
                    "source": run_nid,
                    "target": f"po:{po.id}",
                    "label": "EVALUATES",
                }
            )

    for e in excs:
        exc_nid = f"exception:{e.id}"
        nodes.append(
            {
                "id": exc_nid,
                "type": "Exception",
                "label": f"{e.type} ({e.status})",
                "data": {"severity": e.severity, "rule_id": e.rule_id, "summary": e.summary},
            }
        )
        if runs:
            edges.append(
                {
                    "id": f"e-run-exc-{e.id}",
                    "source": f"recon:{runs[0].id}",
                    "target": exc_nid,
                    "label": "CREATES",
                }
            )

    for inv_case in investigations:
        invst_nid = f"investigation:{inv_case.id}"
        nodes.append(
            {
                "id": invst_nid,
                "type": "Investigation",
                "label": f"Investigation ({inv_case.status})",
                "data": {
                    "model_provider": inv_case.model_provider,
                    "model_name": inv_case.model_name,
                    "confidence": str(inv_case.confidence),
                },
            }
        )
        edges.append(
            {
                "id": f"e-exc-invst-{inv_case.id}",
                "source": f"exception:{inv_case.case_id}",
                "target": invst_nid,
                "label": "INVESTIGATED_BY",
            }
        )

    for ap in approvals:
        ap_nid = f"approval:{ap.id}"
        nodes.append(
            {
                "id": ap_nid,
                "type": "Approval",
                "label": f"{ap.decision} ({ap.amount_evaluated})",
                "data": {"rationale": ap.rationale, "decided_at": ap.decided_at.isoformat()},
            }
        )
        target = f"exception:{ap.case_id}" if ap.case_id else f"po:{ap.transaction_id}"
        edges.append(
            {
                "id": f"e-exc-ap-{ap.id}",
                "source": target,
                "target": ap_nid,
                "label": "REVIEWED_THROUGH",
            }
        )

    unsupported_qty = max(Decimal("0"), total_invoiced - total_accepted)
    outstanding_delivery = max(Decimal("0"), total_ordered - total_accepted)
    exposure_amount = Decimal("0")
    if total_ordered > 0 and unsupported_qty > 0 and total_po_amount > 0:
        exposure_amount = ((total_po_amount / total_ordered) * unsupported_qty).quantize(
            Decimal("0.01")
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "ordered_qty": str(total_ordered),
            "accepted_qty": str(total_accepted),
            "invoiced_qty": str(total_invoiced),
            "outstanding_delivery_qty": str(outstanding_delivery),
            "unsupported_invoiced_qty": str(unsupported_qty),
            "exposure_amount": str(exposure_amount),
            "currency": po.currency if po else (invoices[0].currency if invoices else "INR"),
        },
        "has_payment_records": False,
        "source": "postgresql_relational",
    }
