from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.config import AppConfig
from app.models.domain import (
    Document,
    ExceptionCase,
    ExtractionField,
    GoodsReceipt,
    Invoice,
    MatchResult,
    PurchaseOrder,
    ReconciliationRun,
    RiskSignal,
    ToleranceConfig,
)
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.reconciliation import (
    GRNLineInput,
    InvoiceInput,
    InvoiceLineInput,
    POInput,
    POLineInput,
    ReconciliationInput,
    ReconciliationOutput,
    ToleranceRule,
    reconcile_transaction,
)


def _load_tolerance(
    db: Session,
    organization_id: UUID,
    vendor_id: UUID | None = None,
    item_code: str | None = None,
) -> ToleranceRule:
    repo = OrgScopedRepository(db, ToleranceConfig, organization_id)
    active = list(
        db.scalars(
            repo.base_query()
            .where(ToleranceConfig.is_active.is_(True))
            .order_by(desc(ToleranceConfig.version))
        ).all()
    )
    # Priority: (vendor_id + item_code) > (vendor_id only) > (item_code only) > org default
    candidates = [
        (vendor_id, item_code),
        (vendor_id, None),
        (None, item_code),
        (None, None),
    ]
    for vid, icode in candidates:
        for row in active:
            if row.vendor_id == vid and row.item_code == icode:
                return ToleranceRule(
                    price_abs_tolerance=row.price_abs_tolerance,
                    price_pct_tolerance=row.price_pct_tolerance,
                    qty_abs_tolerance=row.qty_abs_tolerance,
                    qty_pct_tolerance=row.qty_pct_tolerance,
                    tax_abs_tolerance=row.tax_abs_tolerance,
                    allow_partial_billing=row.allow_partial_billing,
                    allow_service_advance_billing=row.allow_service_advance_billing,
                )
    return ToleranceRule()


def _low_confidence_fields_for_tx(
    db: Session,
    organization_id: UUID,
    document_ids: list[UUID],
) -> list[str]:
    if not document_ids:
        return []
    cfg = db.scalar(
        OrgScopedRepository(db, AppConfig, organization_id)
        .base_query()
        .where(AppConfig.is_active.is_(True))
        .order_by(desc(AppConfig.version))
    )
    threshold = Decimal(
        str((cfg.config_json or {}).get("confidence_threshold", "0.80")) if cfg else "0.80"
    )
    doc_repo = OrgScopedRepository(db, Document, organization_id)
    docs = list(db.scalars(doc_repo.base_query().where(Document.id.in_(document_ids))).all())
    flagged: list[str] = []
    for doc in docs:
        fields = list(
            db.scalars(
                OrgScopedRepository(db, ExtractionField, organization_id)
                .base_query()
                .where(
                    ExtractionField.document_id == doc.id,
                    ExtractionField.is_active.is_(True),
                )
            ).all()
        )
        for fld in fields:
            if fld.verification_status == "extracted" and fld.confidence < threshold:
                flagged.append(f"{doc.file_name}:{fld.field_name}")
    return flagged


def execute_reconciliation(
    db: Session,
    *,
    organization_id: UUID,
    transaction_id: UUID,
    actor_type: str,
    actor_id: str,
) -> dict[str, Any]:
    po_repo = OrgScopedRepository(db, PurchaseOrder, organization_id)
    grn_repo = OrgScopedRepository(db, GoodsReceipt, organization_id)
    inv_repo = OrgScopedRepository(db, Invoice, organization_id)

    po = po_repo.get_by_id(transaction_id)
    if po is not None:
        grns = list(
            db.scalars(grn_repo.base_query().where(GoodsReceipt.po_id == po.id)).all()
        )
        invoices = list(
            db.scalars(inv_repo.base_query().where(Invoice.po_id == po.id)).all()
        )
        vendor_id = po.vendor_id
    else:
        standalone = inv_repo.get_by_id(transaction_id)
        if standalone is None:
            raise AppError(
                code="TRANSACTION_NOT_FOUND",
                message="Transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        grns = []
        invoices = [standalone]
        vendor_id = standalone.vendor_id

    doc_ids: list[UUID] = []
    if po and po.document_id:
        doc_ids.append(po.document_id)
    for g in grns:
        if g.document_id:
            doc_ids.append(g.document_id)
    for inv in invoices:
        if inv.document_id:
            doc_ids.append(inv.document_id)

    low_conf = _low_confidence_fields_for_tx(db, organization_id, doc_ids)

    po_input: POInput | None = None
    line_tolerances: dict[str, ToleranceRule] = {}
    if po is not None:
        po_lines = tuple(
            POLineInput(
                line_id=str(ln.id),
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
            for ln in po.lines
        )
        po_input = POInput(
            po_id=str(po.id),
            po_number=po.po_number,
            vendor_id=str(po.vendor_id),
            currency=po.currency,
            subtotal_amount=po.subtotal_amount,
            tax_amount=po.tax_amount,
            discount_amount=po.discount_amount,
            freight_amount=po.freight_amount,
            total_amount=po.total_amount,
            lines=po_lines,
        )
        for ln in po.lines:
            line_tolerances[str(ln.id)] = _load_tolerance(
                db, organization_id, vendor_id=po.vendor_id, item_code=ln.item_code
            )

    grn_line_inputs: list[GRNLineInput] = []
    for g in grns:
        for gl in g.lines:
            grn_line_inputs.append(
                GRNLineInput(
                    grn_id=str(g.id),
                    grn_number=g.grn_number,
                    po_line_id=str(gl.po_line_id) if gl.po_line_id else None,
                    item_code=gl.item_code,
                    uom=gl.uom,
                    received_qty=gl.received_qty,
                    accepted_qty=gl.accepted_qty,
                    rejected_qty=gl.rejected_qty,
                )
            )

    inv_inputs: list[InvoiceInput] = []
    for inv in invoices:
        # Check exact duplicate against another invoice in org+vendor
        dup_other = db.scalar(
            inv_repo.base_query().where(
                Invoice.vendor_id == inv.vendor_id,
                Invoice.id != inv.id,
                Invoice.invoice_number == inv.invoice_number,
            )
        )
        is_dup = bool(inv.duplicate_of_invoice_id or dup_other is not None)
        dup_id = (
            str(inv.duplicate_of_invoice_id)
            if inv.duplicate_of_invoice_id
            else (str(dup_other.id) if dup_other else None)
        )
        inv_inputs.append(
            InvoiceInput(
                invoice_id=str(inv.id),
                invoice_number=inv.invoice_number,
                normalized_invoice_number=inv.normalized_invoice_number,
                vendor_id=str(inv.vendor_id),
                po_id=str(inv.po_id) if inv.po_id else None,
                currency=inv.currency,
                subtotal_amount=inv.subtotal_amount,
                tax_amount=inv.tax_amount,
                discount_amount=inv.discount_amount,
                freight_amount=inv.freight_amount,
                total_amount=inv.total_amount,
                is_exact_duplicate=is_dup,
                duplicate_of_invoice_id=dup_id,
                lines=tuple(
                    InvoiceLineInput(
                        line_id=str(il.id),
                        invoice_id=str(inv.id),
                        po_line_id=str(il.po_line_id) if il.po_line_id else None,
                        item_code=il.item_code,
                        description=il.description,
                        uom=il.uom,
                        quantity=il.quantity,
                        unit_price=il.unit_price,
                        tax_rate=il.tax_rate,
                        tax_amount=il.tax_amount,
                        discount_amount=il.discount_amount,
                        line_total=il.line_total,
                    )
                    for il in inv.lines
                ),
            )
        )

    default_tol = _load_tolerance(db, organization_id, vendor_id=vendor_id, item_code=None)
    recon_input = ReconciliationInput(
        transaction_id=str(transaction_id),
        organization_id=str(organization_id),
        purchase_order=po_input,
        grn_lines=tuple(grn_line_inputs),
        invoices=tuple(inv_inputs),
        default_tolerance=default_tol,
        line_tolerances=line_tolerances,
        low_confidence_fields=tuple(low_conf),
        has_grn_documents=len(grns) > 0,
    )

    started = datetime.now(UTC)
    output: ReconciliationOutput = reconcile_transaction(recon_input)
    completed = datetime.now(UTC)

    run = ReconciliationRun(
        organization_id=organization_id,
        transaction_id=transaction_id,
        rule_version=output.rule_version,
        status="COMPLETED",
        outcome=output.outcome.value,
        totals_json={
            "ordered_total": str(output.ordered_total),
            "accepted_supported_total": str(output.accepted_supported_total),
            "invoiced_total": str(output.invoiced_total),
            "undisputed_amount": str(output.undisputed_amount),
            "disputed_amount": str(output.disputed_amount),
            "currency": output.currency,
            "line_quantities": [
                {
                    "po_line_id": q.po_line_id,
                    "item_code": q.item_code,
                    "uom": q.uom,
                    "ordered_qty": str(q.ordered_qty),
                    "received_qty": str(q.received_qty),
                    "accepted_qty": str(q.accepted_qty),
                    "rejected_qty": str(q.rejected_qty),
                    "invoiced_qty": str(q.invoiced_qty),
                    "remaining_to_receive": str(q.remaining_to_receive),
                    "eligible_to_invoice": str(q.eligible_to_invoice),
                    "potential_over_billing": str(q.potential_over_billing),
                    "potential_under_billing": str(q.potential_under_billing),
                }
                for q in output.line_quantities
            ],
        },
        started_at=started,
        completed_at=completed,
    )
    db.add(run)
    db.flush()

    for rr in output.rule_results:
        db.add(
            MatchResult(
                organization_id=organization_id,
                run_id=run.id,
                entity_line_id=rr.entity_line_id,
                field_name=rr.field_name,
                expected_value=rr.expected_value,
                actual_value=rr.actual_value,
                variance=rr.variance,
                tolerance_applied=rr.tolerance_applied,
                breakdown_json=rr.breakdown,
                rule_id=rr.rule_id,
                result=rr.result.value,
            )
        )

    # Replace previous open auto-generated exceptions before inserting fresh run exceptions
    existing_open_excs = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, organization_id)
            .base_query()
            .where(
                ExceptionCase.transaction_id == transaction_id,
                ExceptionCase.status == "OPEN",
            )
        ).all()
    )
    for old_exc in existing_open_excs:
        db.delete(old_exc)
    db.flush()

    persisted_exceptions: list[dict[str, Any]] = []
    for ed in output.exceptions:
        exc_row = ExceptionCase(
            organization_id=organization_id,
            transaction_id=transaction_id,
            run_id=run.id,
            type=ed.exception_type,
            severity=ed.severity,
            status="OPEN",
            summary=ed.summary,
            affected_fields_json=list(ed.affected_fields),
            values_json=ed.values,
            rule_id=ed.rule_id,
            evidence_refs_json=list(ed.evidence_refs),
            version=1,
        )
        db.add(exc_row)
        db.flush()
        persisted_exceptions.append(
            {
                "case_id": str(exc_row.id),
                "code": exc_row.type,
                "rule_id": exc_row.rule_id,
                "severity": exc_row.severity,
                "expected": ed.values.get("expected", ""),
                "actual": ed.values.get("actual", ""),
                "variance": ed.values.get("variance", ""),
                "summary": exc_row.summary,
            }
        )
        if ed.rule_id == "R-DUP-01":
            db.add(
                RiskSignal(
                    organization_id=organization_id,
                    transaction_id=transaction_id,
                    signal_type="EXACT_DUPLICATE_INVOICE",
                    severity="HIGH",
                    score=Decimal("0.9500"),
                    reason_json={
                        "reason_codes": ["EXACT_DUPLICATE_INVOICE_NUMBER"],
                        "contributing_signals": [ed.summary],
                        "disclaimer": "Risk indicator for review, not proof of fraud.",
                    },
                    model_version="rules-v1",
                )
            )

    # Evaluate active administrator-defined dynamic policies (Donut Challenge 1)
    from app.services.policies.engine import evaluate_active_policies_for_transaction

    policy_results = evaluate_active_policies_for_transaction(
        db,
        organization_id=organization_id,
        transaction_id=transaction_id,
        reconciliation_run_id=run.id,
    )

    # Update transaction status (note: never auto-approves payment; sets match outcome status)
    if po is not None:
        po.status = output.outcome.value
    for inv in invoices:
        inv.status = output.outcome.value

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action="RECONCILIATION_EXECUTED",
        entity_type="reconciliation_run",
        entity_id=str(run.id),
        after={
            "transaction_id": str(transaction_id),
            "outcome": output.outcome.value,
            "exception_count": len(persisted_exceptions),
            "undisputed_amount": str(output.undisputed_amount),
            "disputed_amount": str(output.disputed_amount),
        },
    )
    db.commit()

    return {
        "run_id": str(run.id),
        "transaction_id": str(transaction_id),
        "status": "COMPLETED",
        "outcome": output.outcome.value,
        "rule_version": output.rule_version,
        "totals": run.totals_json,
        "exceptions": persisted_exceptions,
        "policy_evaluations": policy_results,
    }
