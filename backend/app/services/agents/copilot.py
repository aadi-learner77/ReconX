import re
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.permissions import CurrentUserContext
from app.models.audit import AuditEvent
from app.models.domain import (
    ExceptionCase,
    Invoice,
    PurchaseOrder,
    RiskSignal,
    Vendor,
    VendorBankChange,
)
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.llm.adapter import get_llm_provider

WRITE_VERBS = (
    "approve ",
    "pay ",
    "transfer ",
    "delete ",
    "update ",
    "reject ",
    "change bank",
    "drop table",
    "insert into",
)


def _tool_query_transaction_ref(
    db: Session, org_id: UUID, ref_token: str
) -> tuple[str, list[dict[str, str]]]:
    po = db.scalar(
        OrgScopedRepository(db, PurchaseOrder, org_id)
        .base_query()
        .where(PurchaseOrder.po_number.ilike(f"%{ref_token}%"))
    )
    if po:
        excs = list(
            db.scalars(
                OrgScopedRepository(db, ExceptionCase, org_id)
                .base_query()
                .where(ExceptionCase.transaction_id == po.id)
            ).all()
        )
        exc_note = f", {len(excs)} exception(s)" if excs else ", no open exceptions"
        return (
            f"PO {po.po_number}: total {po.total_amount} {po.currency}, "
            f"status={po.status}{exc_note}.",
            [{"type": "transaction", "id": str(po.id), "label": po.po_number}],
        )

    inv = db.scalar(
        OrgScopedRepository(db, Invoice, org_id)
        .base_query()
        .where(Invoice.invoice_number.ilike(f"%{ref_token}%"))
    )
    if inv:
        tx_id = str(inv.po_id or inv.id)
        return (
            f"Invoice {inv.invoice_number}: total {inv.total_amount} {inv.currency}, "
            f"status={inv.status}, due={inv.due_date}.",
            [{"type": "transaction", "id": tx_id, "label": inv.invoice_number}],
        )
    return ("", [])


def _tool_query_exceptions(
    db: Session, org_id: UUID, q_low: str
) -> tuple[str, list[dict[str, str]]]:
    stmt = OrgScopedRepository(db, ExceptionCase, org_id).base_query()
    if "high" in q_low or "critical" in q_low:
        stmt = stmt.where(ExceptionCase.severity == "HIGH")
    if "open" in q_low or "unresolved" in q_low or "pending" in q_low:
        stmt = stmt.where(ExceptionCase.status.notin_(["APPROVED", "REJECTED"]))
    cases = list(db.scalars(stmt.order_by(desc(ExceptionCase.created_at)).limit(10)).all())
    if not cases:
        return ("No matching exception records found in your organization.", [])
    lines = [f"- {c.type} ({c.severity}, {c.status}): {c.summary}" for c in cases[:5]]
    cits = [
        {"type": "transaction", "id": str(c.transaction_id), "label": c.type} for c in cases[:5]
    ]
    return (
        f"Found {len(cases)} exception case(s) in your organization:\n" + "\n".join(lines),
        cits,
    )


def _tool_query_vendors(db: Session, org_id: UUID) -> tuple[str, list[dict[str, str]]]:
    vendors = list(
        db.scalars(OrgScopedRepository(db, Vendor, org_id).base_query().limit(10)).all()
    )
    if not vendors:
        return ("No vendor records found in your organization.", [])
    pending_bank_vids = {
        bc.vendor_id
        for bc in db.scalars(
            OrgScopedRepository(db, VendorBankChange, org_id)
            .base_query()
            .where(VendorBankChange.verification_status == "ENHANCED_VERIFICATION_REQUIRED")
        ).all()
    }
    lines = [
        f"- {v.legal_name} (GSTIN/Tax ID: {v.tax_identifier or 'N/A'}"
        + (", BANK CHANGE PENDING" if v.id in pending_bank_vids else "")
        + ")"
        for v in vendors[:5]
    ]
    cits = [{"type": "vendor", "id": str(v.id), "label": v.legal_name} for v in vendors[:5]]
    return (f"Showing {len(vendors)} vendor(s) in your organization:\n" + "\n".join(lines), cits)


def _tool_query_risks(db: Session, org_id: UUID) -> tuple[str, list[dict[str, str]]]:
    sigs = list(
        db.scalars(
            OrgScopedRepository(db, RiskSignal, org_id)
            .base_query()
            .order_by(desc(RiskSignal.created_at))
            .limit(10)
        ).all()
    )
    if not sigs:
        return ("No risk indicator signals currently persisted in your organization.", [])
    lines = [f"- {s.signal_type} ({s.severity}, score={s.score})" for s in sigs[:5]]
    cits = [
        {"type": "transaction", "id": str(s.transaction_id), "label": s.signal_type}
        for s in sigs[:5]
    ]
    return (
        f"Found {len(sigs)} risk indicator(s) (review signals, not proof of fraud):\n"
        + "\n".join(lines),
        cits,
    )


def _tool_query_cash_forecast(db: Session, org_id: UUID) -> tuple[str, list[dict[str, str]]]:
    today = date.today()
    invs = list(
        db.scalars(
            OrgScopedRepository(db, Invoice, org_id)
            .base_query()
            .where(Invoice.status != "REJECTED")
        ).all()
    )
    if not invs:
        return ("No non-rejected invoices found to forecast cash obligations.", [])
    overdue = sum((i.total_amount for i in invs if (i.due_date - today).days < 0), Decimal("0"))
    due_30 = sum(
        (i.total_amount for i in invs if 0 <= (i.due_date - today).days <= 30), Decimal("0")
    )
    due_60 = sum(
        (i.total_amount for i in invs if 31 <= (i.due_date - today).days <= 60), Decimal("0")
    )
    cits = [
        {"type": "transaction", "id": str(i.po_id or i.id), "label": i.invoice_number}
        for i in invs[:3]
    ]
    return (
        f"Cash obligation summary across {len(invs)} invoice(s): "
        f"Overdue={overdue.quantize(Decimal('0.01'))}, "
        f"Due 0-30d={due_30.quantize(Decimal('0.01'))}, "
        f"Due 31-60d={due_60.quantize(Decimal('0.01'))}.",
        cits,
    )


def _tool_query_audit(db: Session, org_id: UUID) -> tuple[str, list[dict[str, str]]]:
    events = list(
        db.scalars(
            OrgScopedRepository(db, AuditEvent, org_id)
            .base_query()
            .order_by(desc(AuditEvent.timestamp))
            .limit(8)
        ).all()
    )
    if not events:
        return ("No audit events recorded yet.", [])
    lines = [f"- {e.action} on {e.entity_type} ({e.actor_type})" for e in events[:5]]
    return (f"Recent {len(events)} audit event(s):\n" + "\n".join(lines), [])


def _tool_query_invoices(db: Session, org_id: UUID) -> tuple[str, list[dict[str, str]]]:
    invs = list(
        db.scalars(
            OrgScopedRepository(db, Invoice, org_id)
            .base_query()
            .order_by(desc(Invoice.invoice_date))
            .limit(10)
        ).all()
    )
    if not invs:
        return ("No matching invoice records found in your organization.", [])
    lines = [
        f"- {i.invoice_number}: {i.total_amount} {i.currency} "
        f"(status={i.status}, due={i.due_date})"
        for i in invs[:5]
    ]
    cits = [
        {"type": "transaction", "id": str(i.po_id or i.id), "label": i.invoice_number}
        for i in invs[:5]
    ]
    return (f"Retrieved {len(invs)} recent invoice(s):\n" + "\n".join(lines), cits)


def answer_copilot_query(
    db: Session,
    *,
    question: str,
    current_user: CurrentUserContext,
) -> dict[str, Any]:
    """Read-only finance copilot using structured org-scoped DB query tools (FR-UI-05..07)."""
    q_low = question.lower().strip()
    org_id = current_user.organization_id

    if any(v in q_low for v in WRITE_VERBS):
        record_audit_event(
            db,
            organization_id=org_id,
            actor_type="USER",
            actor_id=str(current_user.id),
            action="COPILOT_WRITE_BLOCKED",
            entity_type="copilot",
            entity_id=str(current_user.id),
            after={"question": question[:200]},
        )
        db.commit()
        return {
            "answer": (
                "The finance copilot is strictly read-only. It cannot approve, edit, or execute "
                "payments via chat. Please use the controlled workflow UI."
            ),
            "citations": [],
            "read_only": True,
            "tool_used": "write_guardrail",
            "limitations": "Read-only copilot policy (FR-UI-07).",
        }

    citations: list[dict[str, str]] = []
    answer = ""
    tool_used = "fallback_clarify"

    ref_match = re.search(r"\b((?:PO|INV)-[A-Z0-9-]+)\b", question, re.IGNORECASE)
    if ref_match:
        answer, citations = _tool_query_transaction_ref(db, org_id, ref_match.group(1))
        if answer:
            tool_used = "query_transaction_by_ref"

    if not answer:
        if any(k in q_low for k in ("cash", "forecast", "liquidity", "outflow", "overdue")):
            answer, citations = _tool_query_cash_forecast(db, org_id)
            tool_used = "query_cash_forecast"
        elif any(k in q_low for k in ("risk", "split", "duplicate", "anomal", "fraud", "bank")):
            answer, citations = _tool_query_risks(db, org_id)
            tool_used = "query_risk_signals"
        elif any(k in q_low for k in ("audit", "who approved", "history", "log", "trail")):
            answer, citations = _tool_query_audit(db, org_id)
            tool_used = "query_audit_events"
        elif any(k in q_low for k in ("exception", "mismatch", "over-bill", "variance", "open")):
            answer, citations = _tool_query_exceptions(db, org_id, q_low)
            tool_used = "query_exceptions"
        elif any(k in q_low for k in ("vendor", "supplier")):
            answer, citations = _tool_query_vendors(db, org_id)
            tool_used = "query_vendors"
        elif any(k in q_low for k in ("invoice", "po", "pending", "due", "bill")):
            answer, citations = _tool_query_invoices(db, org_id)
            tool_used = "query_invoices"
        else:
            pos = list(
                db.scalars(
                    OrgScopedRepository(db, PurchaseOrder, org_id).base_query().limit(5)
                ).all()
            )
            if not pos:
                answer = (
                    "No matching records found. Try asking about open exceptions, "
                    "vendors, risk signals, cash forecast, or invoices."
                )
            else:
                answer = (
                    "Could you clarify whether you want to inspect open exceptions, "
                    "vendor profiles, risk signals, cash-flow forecast, or pending invoices?"
                )
                citations = [
                    {"type": "transaction", "id": str(p.id), "label": p.po_number} for p in pos[:3]
                ]

    llm = get_llm_provider()
    record_audit_event(
        db,
        organization_id=org_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="COPILOT_QUERY",
        entity_type="copilot",
        entity_id=str(current_user.id),
        after={
            "question": question[:200],
            "tool_used": tool_used,
            "citation_count": len(citations),
        },
    )
    db.commit()

    return {
        "answer": answer,
        "citations": citations,
        "read_only": True,
        "tool_used": tool_used,
        "provider": llm.provider_name,
        "limitations": "Scoped strictly to your organization via typed read-only retrieval.",
    }
