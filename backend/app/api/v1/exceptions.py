from math import ceil
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, get_current_user, require_permission
from app.models.auth import User
from app.models.domain import Approval, ExceptionCase, ExceptionComment, Investigation, Notification
from app.repositories.base import OrgScopedRepository
from app.schemas.common import PaginatedResponse, paginate_params
from app.services.audit.service import record_audit_event
from app.services.workflows.approval import create_redacted_notification, decide_exception_case
from app.services.workflows.state_machine import validate_transition

router = APIRouter(tags=["exceptions"])


class AssignCaseRequest(BaseModel):
    owner_id: UUID


class CommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    is_clarification_request: bool = False


class DecisionRequest(BaseModel):
    decision: str
    rationale: str = ""
    version: int | None = None


def _case_to_dict(c: ExceptionCase) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "organization_id": str(c.organization_id),
        "transaction_id": str(c.transaction_id),
        "run_id": str(c.run_id) if c.run_id else None,
        "type": c.type,
        "severity": c.severity,
        "status": c.status,
        "owner_id": str(c.owner_id) if c.owner_id else None,
        "created_by": str(c.created_by) if c.created_by else None,
        "summary": c.summary,
        "affected_fields": c.affected_fields_json,
        "values": c.values_json,
        "rule_id": c.rule_id,
        "evidence_refs": c.evidence_refs_json,
        "version": c.version,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


@router.get("/exceptions", response_model=PaginatedResponse[dict[str, Any]])
def list_exceptions(
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    exc_type: str | None = Query(default=None, alias="type"),
    transaction_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[dict[str, Any]]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    stmt = OrgScopedRepository(db, ExceptionCase, current_user.organization_id).base_query()
    if status_filter:
        stmt = stmt.where(ExceptionCase.status == status_filter)
    if severity:
        stmt = stmt.where(ExceptionCase.severity == severity)
    if exc_type:
        stmt = stmt.where(ExceptionCase.type == exc_type)
    if transaction_id:
        stmt = stmt.where(ExceptionCase.transaction_id == transaction_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(desc(ExceptionCase.created_at), asc(ExceptionCase.id))
            .offset(offset)
            .limit(safe_size)
        ).all()
    )
    return PaginatedResponse(
        items=[_case_to_dict(c) for c in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.get("/exceptions/{case_id}")
def get_exception_case(
    case_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("exceptions:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = OrgScopedRepository(db, ExceptionCase, current_user.organization_id).get_by_id(case_id)
    if not case:
        raise AppError("CASE_NOT_FOUND", "Exception case not found.", status.HTTP_404_NOT_FOUND)

    comments = list(
        db.scalars(
            OrgScopedRepository(db, ExceptionComment, current_user.organization_id)
            .base_query()
            .where(ExceptionComment.case_id == case.id)
            .order_by(asc(ExceptionComment.created_at))
        ).all()
    )
    approvals = list(
        db.scalars(
            OrgScopedRepository(db, Approval, current_user.organization_id)
            .base_query()
            .where(Approval.case_id == case.id)
            .order_by(desc(Approval.decided_at))
        ).all()
    )
    investigations = list(
        db.scalars(
            OrgScopedRepository(db, Investigation, current_user.organization_id)
            .base_query()
            .where(Investigation.case_id == case.id)
            .order_by(desc(Investigation.created_at))
        ).all()
    )
    out = _case_to_dict(case)
    out["comments"] = [
        {
            "id": str(cm.id),
            "author_id": str(cm.author_id),
            "body": cm.body,
            "is_clarification_request": cm.is_clarification_request,
            "created_at": cm.created_at.isoformat(),
        }
        for cm in comments
    ]
    out["approvals"] = [
        {
            "id": str(ap.id),
            "approver_id": str(ap.approver_id),
            "decision": ap.decision,
            "rationale": ap.rationale,
            "amount_evaluated": str(ap.amount_evaluated),
            "decided_at": ap.decided_at.isoformat(),
        }
        for ap in approvals
    ]
    out["investigations"] = [
        {
            "id": str(inv.id),
            "agent_version": inv.agent_version,
            "model_provider": inv.model_provider,
            "model_name": inv.model_name,
            "prompt_version": inv.prompt_version,
            "confidence": float(inv.confidence),
            "status": inv.status,
            "structured_output": inv.structured_output_json,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in investigations
    ]
    return out


@router.post("/exceptions/{case_id}/assign")
def assign_exception_case(
    case_id: UUID,
    payload: AssignCaseRequest,
    current_user: CurrentUserContext = Depends(require_permission("exceptions:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = OrgScopedRepository(db, ExceptionCase, current_user.organization_id).get_by_id(case_id)
    if not case:
        raise AppError("CASE_NOT_FOUND", "Exception case not found.", status.HTTP_404_NOT_FOUND)
    assignee = OrgScopedRepository(db, User, current_user.organization_id).get_by_id(
        payload.owner_id
    )
    if not assignee:
        raise AppError("USER_NOT_FOUND", "Assignee user not found.", status.HTTP_404_NOT_FOUND)

    before_owner = str(case.owner_id) if case.owner_id else None
    case.owner_id = assignee.id
    if case.status == "OPEN":
        validate_transition(case.status, "IN_REVIEW")
        case.status = "IN_REVIEW"
    case.version += 1

    # Redacted notification: never expose raw invoice numbers/amounts/bank details in notification
    create_redacted_notification(
        db,
        organization_id=current_user.organization_id,
        recipient_id=assignee.id,
        notif_type="CASE_ASSIGNED",
        reference_id=str(case.id),
        message=f"You have been assigned exception case ({case.type}, severity {case.severity}).",
    )
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CASE_ASSIGNED",
        entity_type="exception_case",
        entity_id=str(case.id),
        before={"owner_id": before_owner},
        after={"owner_id": str(assignee.id), "status": case.status},
    )
    db.commit()
    return _case_to_dict(case)


@router.post("/exceptions/{case_id}/comments", status_code=status.HTTP_201_CREATED)
def add_exception_comment(
    case_id: UUID,
    payload: CommentRequest,
    current_user: CurrentUserContext = Depends(require_permission("exceptions:comment")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    case = OrgScopedRepository(db, ExceptionCase, current_user.organization_id).get_by_id(case_id)
    if not case:
        raise AppError("CASE_NOT_FOUND", "Exception case not found.", status.HTTP_404_NOT_FOUND)

    comment = ExceptionComment(
        organization_id=current_user.organization_id,
        case_id=case.id,
        author_id=current_user.id,
        body=payload.body.strip(),
        is_clarification_request=payload.is_clarification_request,
    )
    db.add(comment)
    if payload.is_clarification_request and case.status in {"OPEN", "IN_REVIEW"}:
        case.status = "INFO_REQUESTED"
        case.version += 1
        if case.owner_id and case.owner_id != current_user.id:
            create_redacted_notification(
                db,
                organization_id=current_user.organization_id,
                recipient_id=case.owner_id,
                notif_type="CLARIFICATION_REQUESTED",
                reference_id=str(case.id),
                message="Clarification requested on an assigned exception case.",
            )

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CASE_COMMENT_ADDED",
        entity_type="exception_case",
        entity_id=str(case.id),
        after={"is_clarification": payload.is_clarification_request},
    )
    db.commit()
    db.refresh(comment)
    return {
        "id": str(comment.id),
        "case_id": str(case.id),
        "author_id": str(comment.author_id),
        "body": comment.body,
        "is_clarification_request": comment.is_clarification_request,
        "created_at": comment.created_at.isoformat(),
    }


@router.post("/exceptions/{case_id}/decision")
def post_exception_decision(
    case_id: UUID,
    payload: DecisionRequest,
    current_user: CurrentUserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return decide_exception_case(
        db,
        case_id=case_id,
        decision=payload.decision,
        rationale=payload.rationale,
        expected_version=payload.version,
        current_user=current_user,
    )


@router.get("/notifications")
def list_my_notifications(
    current_user: CurrentUserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            OrgScopedRepository(db, Notification, current_user.organization_id)
            .base_query()
            .where(Notification.recipient_id == current_user.id)
            .order_by(desc(Notification.created_at))
            .limit(50)
        ).all()
    )
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "reference_id": n.reference_id,
            "message": n.message,
            "status": n.status,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    notif = db.scalar(
        OrgScopedRepository(db, Notification, current_user.organization_id)
        .base_query()
        .where(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
    )
    if not notif:
        raise AppError(
            "NOTIFICATION_NOT_FOUND", "Notification not found.", status.HTTP_404_NOT_FOUND
        )
    notif.status = "READ"
    db.commit()
    return {"id": str(notif.id), "status": notif.status}
