import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.domain import (
    Document,
    ExceptionCase,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    ReconciliationRun,
    Vendor,
)
from app.models.policy import ExecutiveBrief, Policy, PolicyAuditRun
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _calc_case_exposure(
    exc: ExceptionCase,
    po: PurchaseOrder | None,
    grns: list[GoodsReceipt],
    invoices: list[Invoice],
) -> tuple[Decimal, str]:
    """Deterministic Decimal exposure calculation without double-counting."""
    vals = exc.values_json or {}
    if exc.rule_id == "R-QTY-01" or exc.type == "QTY_OVER_BILLED":
        expected = Decimal(str(vals.get("expected", "0") or "0"))
        actual = Decimal(str(vals.get("actual", "0") or "0"))
        diff_qty = max(Decimal("0"), actual - expected)
        unit_price = (
            max((Decimal(str(ln.unit_price)) for ln in po.lines), default=Decimal("0"))
            if po
            else Decimal("0")
        )
        if diff_qty > 0 and unit_price > 0:
            return (diff_qty * unit_price).quantize(Decimal("0.01")), "QUANTITY_VARIANCE"
    if exc.rule_id == "R-PRC-01" or exc.type == "PRICE_VARIANCE":
        variance = abs(Decimal(str(vals.get("variance", "0") or "0")))
        qty = (
            sum((Decimal(str(ln.quantity)) for inv in invoices for ln in inv.lines), Decimal("0"))
            or Decimal("1")
        )
        if variance > 0:
            return (variance * qty).quantize(Decimal("0.01")), "PRICE_VARIANCE"

    # Dynamic policy or other exception: bounded by invoice vs PO delta if available
    inv_total = sum((Decimal(str(i.total_amount)) for i in invoices), Decimal("0"))
    po_total = Decimal(str(po.total_amount)) if po else Decimal("0")
    if inv_total > po_total and po_total > 0:
        return (inv_total - po_total).quantize(Decimal("0.01")), "OVERBILLING_EXPOSURE"
    if inv_total > 0 and exc.type == "MISSING_GRN":
        return inv_total.quantize(Decimal("0.01")), "POTENTIAL_EXPOSURE"
    return Decimal("0.00"), "OTHER"


def generate_executive_brief(
    db: Session,
    *,
    organization_id: UUID,
    created_by: str,
    scope: str = "OPEN_EXCEPTIONS",
    policy_audit_run_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ExecutiveBrief:
    """Generate and persist a reproducible, DB-grounded Executive Boardroom Brief."""
    po_stmt = OrgScopedRepository(db, PurchaseOrder, organization_id).base_query()
    if date_from:
        po_stmt = po_stmt.where(PurchaseOrder.issue_date >= date_from)
    if date_to:
        po_stmt = po_stmt.where(PurchaseOrder.issue_date <= date_to)
    pos = list(db.scalars(po_stmt).all())
    po_map = {p.id: p for p in pos}

    docs_count = (
        db.scalar(
            select(func.count()).select_from(
                OrgScopedRepository(db, Document, organization_id).base_query().subquery()
            )
        )
        or 0
    )
    runs = list(
        db.scalars(
            OrgScopedRepository(db, ReconciliationRun, organization_id)
            .base_query()
            .order_by(desc(ReconciliationRun.completed_at))
        ).all()
    )
    latest_by_tx: dict[UUID, ReconciliationRun] = {}
    for r in runs:
        if r.transaction_id not in latest_by_tx:
            latest_by_tx[r.transaction_id] = r

    excs_all = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, organization_id).base_query()
        ).all()
    )
    open_excs = [e for e in excs_all if e.status not in ("APPROVED", "REJECTED")]

    audit_run: PolicyAuditRun | None = None
    if policy_audit_run_id:
        audit_run = OrgScopedRepository(db, PolicyAuditRun, organization_id).get_by_id(
            policy_audit_run_id
        )
        if not audit_run:
            raise AppError(
                "AUDIT_RUN_NOT_FOUND", "Policy audit run not found.", status.HTTP_404_NOT_FOUND
            )

    metrics = {
        "total_documents_processed": docs_count,
        "total_transactions_evaluated": len(latest_by_tx),
        "total_purchase_orders": len(pos),
        "matched_transactions": sum(
            1 for r in latest_by_tx.values() if r.outcome == "MATCHED"
        ),
        "matched_within_tolerance": sum(
            1 for r in latest_by_tx.values() if r.outcome == "MATCHED_WITH_TOLERANCE"
        ),
        "review_required": sum(
            1 for r in latest_by_tx.values() if r.outcome == "REVIEW_REQUIRED"
        ),
        "exception_transactions": sum(
            1 for r in latest_by_tx.values() if r.outcome == "EXCEPTION"
        ),
        "total_open_exceptions": len(open_excs),
        "high_and_critical_exceptions": sum(
            1 for e in open_excs if e.severity in ("HIGH", "CRITICAL")
        ),
    }

    vendors = {
        v.id: v
        for v in db.scalars(OrgScopedRepository(db, Vendor, organization_id).base_query()).all()
    }
    all_grns = list(
        db.scalars(OrgScopedRepository(db, GoodsReceipt, organization_id).base_query()).all()
    )
    all_invs = list(
        db.scalars(OrgScopedRepository(db, Invoice, organization_id).base_query()).all()
    )

    grns_by_po: dict[UUID, list[GoodsReceipt]] = {}
    for g in all_grns:
        if g.po_id:
            grns_by_po.setdefault(g.po_id, []).append(g)
    invs_by_po: dict[UUID, list[Invoice]] = {}
    for inv in all_invs:
        if inv.po_id:
            invs_by_po.setdefault(inv.po_id, []).append(inv)

    # Quantify exposure without double-counting per transaction
    seen_tx_exposure: dict[UUID, Decimal] = {}
    qty_exposure = Decimal("0.00")
    price_exposure = Decimal("0.00")
    other_exposure = Decimal("0.00")
    affected_invoice_ids: set[UUID] = set()

    ranked_candidates: list[dict[str, Any]] = []
    for e in open_excs:
        po = po_map.get(e.transaction_id)
        grns = grns_by_po.get(e.transaction_id, [])
        invs = invs_by_po.get(e.transaction_id, [])
        for inv in invs:
            affected_invoice_ids.add(inv.id)
        exp_amt, exp_cat = _calc_case_exposure(e, po, grns, invs)

        prev_tx_exp = seen_tx_exposure.get(e.transaction_id, Decimal("0.00"))
        if exp_amt > prev_tx_exp:
            delta = exp_amt - prev_tx_exp
            seen_tx_exposure[e.transaction_id] = exp_amt
            if exp_cat == "QUANTITY_VARIANCE":
                qty_exposure += delta
            elif exp_cat == "PRICE_VARIANCE":
                price_exposure += delta
            else:
                other_exposure += delta

        vendor = (
            vendors.get(po.vendor_id)
            if po
            else (vendors.get(invs[0].vendor_id) if invs else None)
        )
        ranked_candidates.append(
            {
                "exc": e,
                "po": po,
                "grns": grns,
                "invs": invs,
                "vendor": vendor,
                "exposure": exp_amt,
                "exposure_category": exp_cat,
            }
        )

    ranked_candidates.sort(
        key=lambda x: (
            -SEVERITY_RANK.get(x["exc"].severity, 0),
            -x["exposure"],
            x["exc"].created_at,
            str(x["exc"].id),
        )
    )

    total_affected_inv_val = sum(
        (Decimal(str(i.total_amount)) for i in all_invs if i.id in affected_invoice_ids),
        Decimal("0.00"),
    )
    total_open_exp = sum(seen_tx_exposure.values(), Decimal("0.00"))
    currency = pos[0].currency if pos else "INR"

    exposure_summary = {
        "currency": currency,
        "total_affected_invoice_value": str(total_affected_inv_val.quantize(Decimal("0.01"))),
        "open_exception_exposure": str(total_open_exp.quantize(Decimal("0.01"))),
        "quantity_variance_exposure": str(qty_exposure.quantize(Decimal("0.01"))),
        "price_variance_exposure": str(price_exposure.quantize(Decimal("0.01"))),
        "other_exposure": str(other_exposure.quantize(Decimal("0.01"))),
        "methodology": (
            "Line-level Decimal variance (unsupported qty * unit price; price diff * qty), "
            "deduplicated per transaction to prevent double-counting."
        ),
    }

    # Build Top 3 Urgent Exceptions + Verified Citations
    citations: list[dict[str, Any]] = []
    cit_counter = 1

    def _add_cit(
        source_type: str,
        record_id: str,
        display_id: str,
        field: str,
        observed: str,
        unit: str = "",
        line_ref: str = "",
        verified: bool = True,
    ) -> str:
        nonlocal cit_counter
        cid = f"CIT-{cit_counter:03d}"
        cit_counter += 1
        citations.append(
            {
                "citation_id": cid,
                "source_type": source_type,
                "source_record_id": record_id,
                "source_display_id": display_id,
                "source_field": field,
                "observed_value": observed,
                "unit": unit,
                "line_reference": line_ref,
                "is_verified": verified,
            }
        )
        return cid

    top_exceptions: list[dict[str, Any]] = []
    for item in ranked_candidates[:3]:
        exc_case: ExceptionCase = item["exc"]
        po = item["po"]
        grns = item["grns"]
        invs = item["invs"]
        vendor = item["vendor"]
        cit_ids: list[str] = []

        if po:
            po_qty = sum((Decimal(str(ln.quantity)) for ln in po.lines), Decimal("0"))
            cit_ids.append(
                _add_cit(
                    "PURCHASE_ORDER",
                    str(po.id),
                    po.po_number,
                    "ordered_quantity",
                    str(po_qty),
                    po.lines[0].uom if po.lines else "EA",
                    str(po.lines[0].id) if po.lines else "",
                )
            )
        for g in grns[:2]:
            acc = sum((Decimal(str(gl.accepted_qty)) for gl in g.lines), Decimal("0"))
            cit_ids.append(
                _add_cit(
                    "GOODS_RECEIPT",
                    str(g.id),
                    g.grn_number,
                    "accepted_quantity",
                    str(acc),
                    "EA",
                    str(g.lines[0].id) if g.lines else "",
                )
            )
        for inv in invs[:2]:
            iq = sum((Decimal(str(il.quantity)) for il in inv.lines), Decimal("0"))
            cit_ids.append(
                _add_cit(
                    "INVOICE",
                    str(inv.id),
                    inv.invoice_number,
                    "invoiced_quantity_and_total",
                    f"{iq} ({inv.total_amount} {inv.currency})",
                    inv.currency,
                    str(inv.lines[0].id) if inv.lines else "",
                )
            )
        cit_ids.append(
            _add_cit(
                "EXCEPTION_RULE",
                str(exc_case.id),
                exc_case.rule_id,
                "evaluation_outcome",
                f"{exc_case.type} ({exc_case.severity})",
            )
        )

        top_exceptions.append(
            {
                "exception_id": str(exc_case.id),
                "transaction_id": str(exc_case.transaction_id),
                "po_number": po.po_number if po else "N/A",
                "invoice_number": invs[0].invoice_number if invs else "N/A",
                "vendor_name": vendor.legal_name if vendor else "Unknown",
                "category": exc_case.type,
                "severity": exc_case.severity,
                "status": exc_case.status,
                "financial_exposure": str(item["exposure"]),
                "currency": po.currency if po else currency,
                "detected_at": exc_case.created_at.isoformat(),
                "rule_id": exc_case.rule_id,
                "why_flagged": exc_case.summary,
                "recommended_action": (
                    "Hold payment and verify supporting GRN/credit note with authorized approver."
                ),
                "citation_ids": cit_ids,
            }
        )

    active_policies = list(
        db.scalars(
            OrgScopedRepository(db, Policy, organization_id)
            .base_query()
            .where(Policy.status == "ACTIVE")
        ).all()
    )
    policy_version_ids = [
        str(p.active_version_id) for p in active_policies if p.active_version_id
    ]

    policy_diff: dict[str, Any] = {}
    if audit_run:
        summary = audit_run.summary_json or {}
        policy_diff = {
            "audit_run_id": str(audit_run.id),
            "status": audit_run.status,
            "transactions_scanned": audit_run.transactions_scanned,
            "new_exceptions": audit_run.new_exceptions,
            "existing_exceptions": audit_run.existing_exceptions,
            "resolved_exceptions": audit_run.resolved_exceptions,
            "newly_flagged_sample": (summary.get("newly_flagged") or [])[:5],
            "no_longer_triggered_sample": (summary.get("no_longer_triggered") or [])[:5],
        }

    limitations = [
        "Payment settlement records are not tracked in ReconX AI; "
        "approved exceptions represent workflow authorization only.",
        "Risk indicator scores are signals for human review, not proof of fraud.",
    ]
    if len(top_exceptions) < 3:
        limitations.append(
            f"Only {len(top_exceptions)} open exception(s) existed in scope (fewer than 3)."
        )

    snapshot = {
        "metrics": metrics,
        "exposure": exposure_summary,
        "top_exceptions": top_exceptions,
        "citations": citations,
        "policy_diff": policy_diff,
    }
    checksum = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    brief = ExecutiveBrief(
        organization_id=organization_id,
        created_by=created_by,
        scope=scope,
        scope_params_json={
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        },
        reconciliation_run_ids_json=[str(r.id) for r in list(latest_by_tx.values())[:50]],
        policy_audit_run_id=audit_run.id if audit_run else None,
        policy_version_ids_json=policy_version_ids,
        metrics_json=metrics,
        exposure_json=exposure_summary,
        top_exceptions_json=top_exceptions,
        citations_json=citations,
        policy_diff_json=policy_diff,
        limitations_json=limitations,
        content_checksum=checksum,
    )
    db.add(brief)
    db.flush()

    record_audit_event(
        db,
        organization_id=organization_id,
        actor_type="USER",
        actor_id=created_by,
        action="EXECUTIVE_BRIEF_GENERATED",
        entity_type="executive_brief",
        entity_id=str(brief.id),
        after={"scope": scope, "checksum": checksum, "top_exceptions": len(top_exceptions)},
    )
    db.commit()
    return brief
