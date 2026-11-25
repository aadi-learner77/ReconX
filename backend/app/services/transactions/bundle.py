import re
from uuid import UUID

from fastapi import status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.domain import (
    ExceptionCase,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    Vendor,
)
from app.repositories.base import OrgScopedRepository
from app.schemas.domain import (
    GoodsReceiptResponse,
    GRNLineResponse,
    InvoiceLineResponse,
    InvoiceResponse,
    POLineResponse,
    PurchaseOrderResponse,
    TransactionBundleResponse,
    VendorResponse,
)


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize_invoice_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper().strip())


def po_to_response(po: PurchaseOrder) -> PurchaseOrderResponse:
    return PurchaseOrderResponse(
        id=po.id,
        organization_id=po.organization_id,
        vendor_id=po.vendor_id,
        po_number=po.po_number,
        issue_date=po.issue_date,
        currency=po.currency,
        status=po.status,
        subtotal_amount=po.subtotal_amount,
        tax_amount=po.tax_amount,
        discount_amount=po.discount_amount,
        freight_amount=po.freight_amount,
        total_amount=po.total_amount,
        scenario_label=po.scenario_label,
        lines=[
            POLineResponse(
                id=ln.id,
                line_number=ln.line_number,
                item_code=ln.item_code,
                description=ln.description,
                uom=ln.uom,
                quantity=ln.quantity,
                unit_price=ln.unit_price,
                tax_rate=ln.tax_rate,
                tax_amount=ln.tax_amount,
                discount_amount=ln.discount_amount,
                line_total=ln.line_total,
            )
            for ln in sorted(po.lines, key=lambda x: x.line_number)
        ],
    )


def grn_to_response(grn: GoodsReceipt) -> GoodsReceiptResponse:
    return GoodsReceiptResponse(
        id=grn.id,
        organization_id=grn.organization_id,
        vendor_id=grn.vendor_id,
        grn_number=grn.grn_number,
        po_id=grn.po_id,
        received_at=grn.received_at,
        status=grn.status,
        scenario_label=grn.scenario_label,
        lines=[
            GRNLineResponse(
                id=ln.id,
                po_line_id=ln.po_line_id,
                item_code=ln.item_code,
                description=ln.description,
                received_qty=ln.received_qty,
                accepted_qty=ln.accepted_qty,
                rejected_qty=ln.rejected_qty,
                uom=ln.uom,
            )
            for ln in grn.lines
        ],
    )


def invoice_to_response(inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=inv.id,
        organization_id=inv.organization_id,
        vendor_id=inv.vendor_id,
        invoice_number=inv.invoice_number,
        normalized_invoice_number=inv.normalized_invoice_number,
        po_id=inv.po_id,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        currency=inv.currency,
        subtotal_amount=inv.subtotal_amount,
        tax_amount=inv.tax_amount,
        discount_amount=inv.discount_amount,
        freight_amount=inv.freight_amount,
        total_amount=inv.total_amount,
        status=inv.status,
        scenario_label=inv.scenario_label,
        duplicate_of_invoice_id=inv.duplicate_of_invoice_id,
        lines=[
            InvoiceLineResponse(
                id=ln.id,
                po_line_id=ln.po_line_id,
                item_code=ln.item_code,
                description=ln.description,
                uom=ln.uom,
                quantity=ln.quantity,
                unit_price=ln.unit_price,
                tax_rate=ln.tax_rate,
                tax_amount=ln.tax_amount,
                discount_amount=ln.discount_amount,
                line_total=ln.line_total,
            )
            for ln in inv.lines
        ],
    )


def vendor_to_response(v: Vendor) -> VendorResponse:
    return VendorResponse(
        id=v.id,
        organization_id=v.organization_id,
        legal_name=v.legal_name,
        normalized_name=v.normalized_name,
        tax_identifier=v.tax_identifier,
        bank_account_masked=v.bank_account_masked,
        status=v.status,
        created_at=v.created_at,
    )


def get_transaction_bundle(
    db: Session,
    organization_id: UUID,
    transaction_id: UUID,
) -> TransactionBundleResponse:
    """Resolve a transaction bundle by PurchaseOrder ID, or standalone Invoice ID (AT-06)."""
    po_repo = OrgScopedRepository(db, PurchaseOrder, organization_id)
    inv_repo = OrgScopedRepository(db, Invoice, organization_id)
    grn_repo = OrgScopedRepository(db, GoodsReceipt, organization_id)
    vendor_repo = OrgScopedRepository(db, Vendor, organization_id)

    po = po_repo.get_by_id(transaction_id)
    if po is not None:
        vendor = vendor_repo.get_by_id(po.vendor_id)
        if not vendor:
            raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
        grns = list(
            db.scalars(
                grn_repo.base_query()
                .where(GoodsReceipt.po_id == po.id)
                .order_by(GoodsReceipt.received_at)
            ).all()
        )
        invoices = list(
            db.scalars(
                inv_repo.base_query()
                .where(Invoice.po_id == po.id)
                .order_by(Invoice.invoice_date, Invoice.created_at)
            ).all()
        )
        tx_status = po.status
        bundle_po: PurchaseOrderResponse | None = po_to_response(po)
    else:
        standalone_inv = inv_repo.get_by_id(transaction_id)
        if standalone_inv is None:
            raise AppError(
                code="TRANSACTION_NOT_FOUND",
                message="Transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        vendor = vendor_repo.get_by_id(standalone_inv.vendor_id)
        if not vendor:
            raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
        grns = []
        invoices = [standalone_inv]
        tx_status = standalone_inv.status
        bundle_po = None

    run_repo = OrgScopedRepository(db, ReconciliationRun, organization_id)
    latest_run = db.scalar(
        run_repo.base_query()
        .where(ReconciliationRun.transaction_id == transaction_id)
        .order_by(desc(ReconciliationRun.completed_at))
    )
    exc_repo = OrgScopedRepository(db, ExceptionCase, organization_id)
    exceptions = list(
        db.scalars(
            exc_repo.base_query()
            .where(ExceptionCase.transaction_id == transaction_id)
            .order_by(desc(ExceptionCase.created_at))
        ).all()
    )
    risk_repo = OrgScopedRepository(db, RiskSignal, organization_id)
    risks = list(
        db.scalars(
            risk_repo.base_query()
            .where(RiskSignal.transaction_id == transaction_id)
            .order_by(desc(RiskSignal.created_at))
        ).all()
    )

    latest_recon_dict = None
    if latest_run:
        latest_recon_dict = {
            "run_id": str(latest_run.id),
            "outcome": latest_run.outcome,
            "rule_version": latest_run.rule_version,
            "totals": latest_run.totals_json,
            "completed_at": latest_run.completed_at.isoformat(),
            "results": [
                {
                    "id": str(r.id),
                    "entity_line_id": r.entity_line_id,
                    "field_name": r.field_name,
                    "expected_value": r.expected_value,
                    "actual_value": r.actual_value,
                    "variance": r.variance,
                    "tolerance_applied": r.tolerance_applied,
                    "breakdown": r.breakdown_json,
                    "rule_id": r.rule_id,
                    "result": r.result,
                }
                for r in latest_run.results
            ],
        }

    return TransactionBundleResponse(
        transaction_id=transaction_id,
        organization_id=organization_id,
        vendor=vendor_to_response(vendor),
        purchase_order=bundle_po,
        goods_receipts=[grn_to_response(g) for g in grns],
        invoices=[invoice_to_response(i) for i in invoices],
        current_status=tx_status,
        latest_reconciliation=latest_recon_dict,
        exceptions=[
            {
                "id": str(e.id),
                "type": e.type,
                "severity": e.severity,
                "status": e.status,
                "rule_id": e.rule_id,
                "summary": e.summary,
                "affected_fields": e.affected_fields_json,
                "values": e.values_json,
                "evidence_refs": e.evidence_refs_json,
                "owner_id": str(e.owner_id) if e.owner_id else None,
                "version": e.version,
            }
            for e in exceptions
        ],
        risk_signals=[
            {
                "id": str(s.id),
                "signal_type": s.signal_type,
                "severity": s.severity,
                "score": str(s.score),
                "reason": s.reason_json,
                "model_version": s.model_version,
                "label": "Risk indicator — for human review, not proof of fraud.",
            }
            for s in risks
        ],
    )
