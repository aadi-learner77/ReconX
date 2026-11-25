import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.audit import AuditEvent
from app.models.domain import (
    Document,
    ExceptionCase,
    Investigation,
    Invoice,
    Job,
    PurchaseOrder,
    ReconciliationRun,
    Vendor,
    VendorBankChange,
)
from app.repositories.base import OrgScopedRepository
from app.services.agents.copilot import answer_copilot_query
from app.services.agents.investigator import run_case_investigation
from app.services.audit.service import record_audit_event
from app.services.graph.builder import build_transaction_evidence_graph
from app.services.risk.engine import compute_vendor_profile, evaluate_transaction_risk

router = APIRouter(tags=["intelligence"])


class BankChangeRequest(BaseModel):
    new_bank_account_masked: str = Field(min_length=4, max_length=64)


class CopilotQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@router.get("/transactions/{transaction_id}/risk")
def get_transaction_risk(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    signals = evaluate_transaction_risk(
        db,
        organization_id=current_user.organization_id,
        transaction_id=transaction_id,
        persist=True,
    )
    return {
        "transaction_id": str(transaction_id),
        "disclaimer": "Risk indicators are signals for human review, not proof of fraud.",
        "signals": signals,
    }


@router.get("/vendors/{vendor_id}/profile")
def get_vendor_profile(
    vendor_id: UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: CurrentUserContext = Depends(require_permission("vendors:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = compute_vendor_profile(
        db,
        organization_id=current_user.organization_id,
        vendor_id=vendor_id,
        date_from=date_from,
        date_to=date_to,
    )
    if not profile:
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
    return profile


@router.post("/vendors/{vendor_id}/bank-change", status_code=status.HTTP_201_CREATED)
def record_vendor_bank_change(
    vendor_id: UUID,
    payload: BankChangeRequest,
    current_user: CurrentUserContext = Depends(require_permission("vendors:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    vendor = OrgScopedRepository(db, Vendor, current_user.organization_id).get_by_id(vendor_id)
    if not vendor:
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)

    evt = VendorBankChange(
        organization_id=current_user.organization_id,
        vendor_id=vendor.id,
        previous_masked=vendor.bank_account_masked,
        new_masked=payload.new_bank_account_masked,
        requested_by=str(current_user.id),
        verification_status="ENHANCED_VERIFICATION_REQUIRED",
    )
    db.add(evt)
    db.flush()

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="VENDOR_BANK_CHANGE_REQUESTED",
        entity_type="vendor_bank_change",
        entity_id=str(evt.id),
        before={"bank_account_masked": vendor.bank_account_masked},
        after={
            "new_masked": payload.new_bank_account_masked,
            "verification_status": evt.verification_status,
        },
    )
    db.commit()
    return {
        "id": str(evt.id),
        "vendor_id": str(vendor.id),
        "verification_status": evt.verification_status,
        "message": (
            "Enhanced human verification required; never accepted solely on AI recommendation."
        ),
    }


@router.post("/exceptions/{case_id}/investigations", status_code=status.HTTP_201_CREATED)
def start_investigation(
    case_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("investigations:run")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return run_case_investigation(db, case_id=case_id, current_user=current_user)


@router.get("/investigations/{investigation_id}")
def get_investigation(
    investigation_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    inv = OrgScopedRepository(db, Investigation, current_user.organization_id).get_by_id(
        investigation_id
    )
    if not inv:
        raise AppError(
            "INVESTIGATION_NOT_FOUND", "Investigation not found.", status.HTTP_404_NOT_FOUND
        )
    return {
        "investigation_id": str(inv.id),
        "case_id": str(inv.case_id),
        "status": inv.status,
        "agent_version": inv.agent_version,
        "model_provider": inv.model_provider,
        "model_name": inv.model_name,
        "prompt_version": inv.prompt_version,
        "confidence": float(inv.confidence),
        "created_at": inv.created_at.isoformat(),
        **inv.structured_output_json,
    }


@router.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org_id = current_user.organization_id
    docs_count = (
        db.scalar(
            select(func.count()).select_from(
                OrgScopedRepository(db, Document, org_id).base_query().subquery()
            )
        )
        or 0
    )
    po_rows = list(db.scalars(OrgScopedRepository(db, PurchaseOrder, org_id).base_query()).all())
    runs = list(
        db.scalars(
            OrgScopedRepository(db, ReconciliationRun, org_id)
            .base_query()
            .order_by(desc(ReconciliationRun.completed_at))
        ).all()
    )
    latest_by_tx: dict[UUID, str] = {}
    for r in runs:
        if r.transaction_id not in latest_by_tx:
            latest_by_tx[r.transaction_id] = r.outcome

    outcome_counts: dict[str, int] = {
        "MATCHED": 0,
        "MATCHED_WITH_TOLERANCE": 0,
        "EXCEPTION": 0,
        "INCOMPLETE": 0,
        "REVIEW_REQUIRED": 0,
    }
    for oc in latest_by_tx.values():
        outcome_counts[oc] = outcome_counts.get(oc, 0) + 1

    open_excs = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionCase, org_id)
            .base_query()
            .where(ExceptionCase.status.notin_(["APPROVED", "REJECTED"]))
            .order_by(desc(ExceptionCase.created_at))
            .limit(10)
        ).all()
    )
    jobs = list(db.scalars(OrgScopedRepository(db, Job, org_id).base_query()).all())
    job_counts = {
        "QUEUED": sum(1 for j in jobs if j.status == "QUEUED"),
        "PROCESSING": sum(1 for j in jobs if j.status == "PROCESSING"),
        "SUCCEEDED": sum(1 for j in jobs if j.status == "SUCCEEDED"),
        "FAILED": sum(1 for j in jobs if j.status == "FAILED"),
    }
    recent_audit = list(
        db.scalars(
            OrgScopedRepository(db, AuditEvent, org_id)
            .base_query()
            .order_by(desc(AuditEvent.timestamp))
            .limit(10)
        ).all()
    )

    return {
        "kpis": {
            "documents": docs_count,
            "transactions": len(po_rows),
            "matched_cases": outcome_counts["MATCHED"] + outcome_counts["MATCHED_WITH_TOLERANCE"],
            "open_exceptions": len(open_excs),
            "pending_approvals": sum(
                1 for e in open_excs if e.status in {"OPEN", "IN_REVIEW", "ESCALATED"}
            ),
            "processing_jobs": job_counts["QUEUED"] + job_counts["PROCESSING"],
        },
        "outcome_breakdown": [{"outcome": k, "count": v} for k, v in outcome_counts.items()],
        "job_status": job_counts,
        "exception_queue": [
            {
                "id": str(e.id),
                "transaction_id": str(e.transaction_id),
                "type": e.type,
                "severity": e.severity,
                "status": e.status,
                "summary": e.summary,
            }
            for e in open_excs
        ],
        "recent_activity": [
            {
                "id": str(a.id),
                "action": a.action,
                "entity_type": a.entity_type,
                "actor_type": a.actor_type,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in recent_audit
        ],
    }


@router.get("/graph/transactions/{transaction_id}")
def get_transaction_graph(
    transaction_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_evidence_graph:
        raise AppError(
            "FEATURE_DISABLED",
            "Financial Evidence Graph feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return build_transaction_evidence_graph(
        db, organization_id=current_user.organization_id, transaction_id=transaction_id
    )


@router.post("/copilot/query")
def copilot_query(
    payload: CopilotQueryRequest,
    current_user: CurrentUserContext = Depends(require_permission("copilot:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_finance_copilot:
        raise AppError(
            "FEATURE_DISABLED",
            "Finance copilot feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return answer_copilot_query(db, question=payload.question, current_user=current_user)


@router.get("/analytics/cash-obligations")
def get_cash_obligations(
    current_user: CurrentUserContext = Depends(require_permission("transactions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not get_settings().feature_cash_view:
        raise AppError(
            "FEATURE_DISABLED",
            "Cash obligations feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    org_id = current_user.organization_id
    today = date.today()
    invs = list(
        db.scalars(
            OrgScopedRepository(db, Invoice, org_id)
            .base_query()
            .where(Invoice.status != "REJECTED")
        ).all()
    )
    vendors = {
        v.id: v.legal_name
        for v in db.scalars(OrgScopedRepository(db, Vendor, org_id).base_query()).all()
    }

    buckets: dict[str, Decimal] = {
        "OVERDUE": Decimal("0"),
        "DUE_0_30": Decimal("0"),
        "DUE_31_60": Decimal("0"),
        "DUE_60_PLUS": Decimal("0"),
    }
    by_vendor: dict[str, Decimal] = {}
    for inv in invs:
        days = (inv.due_date - today).days
        if days < 0:
            buckets["OVERDUE"] += inv.total_amount
        elif days <= 30:
            buckets["DUE_0_30"] += inv.total_amount
        elif days <= 60:
            buckets["DUE_31_60"] += inv.total_amount
        else:
            buckets["DUE_60_PLUS"] += inv.total_amount
        vname = vendors.get(inv.vendor_id, "Unknown")
        by_vendor[vname] = by_vendor.get(vname, Decimal("0")) + inv.total_amount

    return {
        "buckets": [{"bucket": k, "amount": str(v)} for k, v in buckets.items()],
        "by_vendor": [
            {"vendor": k, "amount": str(v)}
            for k, v in sorted(by_vendor.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "note": (
            "Aggregation of non-rejected invoices by due date; "
            "trend forecast is illustrative only."
        ),
    }


@router.get("/reports/export")
def export_report(
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    current_user: CurrentUserContext = Depends(require_permission("reports:export")),
    db: Session = Depends(get_db),
) -> Response:
    if not get_settings().feature_report_exports:
        raise AppError(
            "FEATURE_DISABLED",
            "Report exports feature flag is disabled.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    org_id = current_user.organization_id
    pos = list(
        db.scalars(
            OrgScopedRepository(db, PurchaseOrder, org_id)
            .base_query()
            .order_by(desc(PurchaseOrder.issue_date))
        ).all()
    )
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["PO Number", "Issue Date", "Currency", "Total Amount", "Status", "Scenario"]
        )
        for p in pos:
            writer.writerow(
                [
                    p.po_number,
                    str(p.issue_date),
                    p.currency,
                    str(p.total_amount),
                    p.status,
                    p.scenario_label or "",
                ]
            )
        return Response(
            content=buf.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="reconx_report.csv"'},
        )

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 800, "ReconX AI — Reconciliation Report")
    c.setFont("Helvetica", 10)
    y = 770
    for p in pos[:35]:
        line_txt = f"{p.po_number} | {p.issue_date} | {p.currency} {p.total_amount} | {p.status}"
        c.drawString(40, y, line_txt)
        y -= 18
        if y < 50:
            break
    c.save()
    return Response(
        content=pdf_buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reconx_report.pdf"'},
    )
