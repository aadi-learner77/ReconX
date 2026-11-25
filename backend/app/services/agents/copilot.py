from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.permissions import CurrentUserContext
from app.models.domain import ExceptionCase, Invoice, PurchaseOrder, Vendor
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.llm.adapter import get_llm_provider


def answer_copilot_query(
    db: Session,
    *,
    question: str,
    current_user: CurrentUserContext,
) -> dict[str, Any]:
    """Read-only finance copilot using typed org-scoped retrieval (FR-UI-05..07)."""
    q_low = question.lower().strip()
    org_id = current_user.organization_id

    # Guardrail: explicitly refuse write/approval/payment commands via chat (FR-UI-07)
    write_verbs = ("approve ", "pay ", "transfer ", "delete ", "update ", "reject ", "change bank")
    if any(v in q_low for v in write_verbs):
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
            "limitations": "Read-only copilot policy (FR-UI-07).",
        }

    # Intent routing to typed, org-scoped retrieval functions (NO text-to-SQL!)
    citations: list[dict[str, str]] = []
    answer = ""

    if "exception" in q_low or "mismatch" in q_low or "over-bill" in q_low or "open" in q_low:
        cases = list(
            db.scalars(
                OrgScopedRepository(db, ExceptionCase, org_id)
                .base_query()
                .order_by(desc(ExceptionCase.created_at))
                .limit(10)
            ).all()
        )
        if not cases:
            answer = "No matching exception records found in your organization."
        else:
            lines = [f"- {c.type} ({c.severity}, {c.status}): {c.summary}" for c in cases[:5]]
            citations = [
                {"type": "transaction", "id": str(c.transaction_id), "label": c.type}
                for c in cases[:5]
            ]
            answer = (
                f"Found {len(cases)} exception case(s) in your organization:\n"
                + "\n".join(lines)
            )
    elif "vendor" in q_low or "supplier" in q_low:
        vendors = list(
            db.scalars(OrgScopedRepository(db, Vendor, org_id).base_query().limit(10)).all()
        )
        if not vendors:
            answer = "No vendor records found in your organization."
        else:
            lines = [
                f"- {v.legal_name} (GSTIN/Tax ID: {v.tax_identifier or 'N/A'})"
                for v in vendors[:5]
            ]
            citations = [
                {"type": "vendor", "id": str(v.id), "label": v.legal_name} for v in vendors[:5]
            ]
            answer = (
                f"Showing {len(vendors)} vendor(s) in your organization:\n" + "\n".join(lines)
            )
    elif "invoice" in q_low or "po" in q_low or "pending" in q_low or "due" in q_low:
        invs = list(
            db.scalars(
                OrgScopedRepository(db, Invoice, org_id)
                .base_query()
                .order_by(desc(Invoice.invoice_date))
                .limit(10)
            ).all()
        )
        if not invs:
            answer = "No matching invoice records found in your organization."
        else:
            lines = [
                f"- {i.invoice_number}: {i.total_amount} {i.currency} "
                f"(status={i.status}, due={i.due_date})"
                for i in invs[:5]
            ]
            citations = [
                {
                    "type": "transaction",
                    "id": str(i.po_id or i.id),
                    "label": i.invoice_number,
                }
                for i in invs[:5]
            ]
            answer = f"Retrieved {len(invs)} recent invoice(s):\n" + "\n".join(lines)
    else:
        pos = list(
            db.scalars(OrgScopedRepository(db, PurchaseOrder, org_id).base_query().limit(5)).all()
        )
        if not pos:
            answer = (
                "No matching records found. "
                "Try asking about open exceptions, vendors, or invoices."
            )
        else:
            answer = (
                "Could you clarify whether you want to inspect open exceptions, vendor profiles, "
                "or pending invoices? You can also use the Transactions dashboard filters."
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
        after={"question": question[:200], "citation_count": len(citations)},
    )
    db.commit()

    return {
        "answer": answer,
        "citations": citations,
        "read_only": True,
        "provider": llm.provider_name,
        "limitations": "Scoped strictly to your organization via typed read-only retrieval.",
    }
