from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.auth import Organization
from app.models.policy import ExecutiveBrief
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.reports.executive_brief import generate_executive_brief
from app.services.reports.renderers import (
    render_brief_csv,
    render_brief_markdown,
    render_brief_pdf,
)

router = APIRouter(tags=["executive-briefs"])


class ExecutiveBriefCreateRequest(BaseModel):
    scope: str = Field(default="OPEN_EXCEPTIONS", max_length=64)
    policy_audit_run_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None


def _serialize_brief(b: ExecutiveBrief) -> dict[str, Any]:
    return {
        "id": str(b.id),
        "scope": b.scope,
        "scope_params": b.scope_params_json,
        "policy_audit_run_id": str(b.policy_audit_run_id) if b.policy_audit_run_id else None,
        "policy_version_ids": b.policy_version_ids_json,
        "metrics": b.metrics_json,
        "exposure": b.exposure_json,
        "top_exceptions": b.top_exceptions_json,
        "citations": b.citations_json,
        "policy_diff": b.policy_diff_json,
        "limitations": b.limitations_json,
        "content_checksum": b.content_checksum,
        "created_by": b.created_by,
        "created_at": b.created_at.isoformat(),
    }


@router.post("/executive-briefs", status_code=status.HTTP_201_CREATED)
def create_executive_brief(
    payload: ExecutiveBriefCreateRequest,
    current_user: CurrentUserContext = Depends(require_permission("reports:generate")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    brief = generate_executive_brief(
        db,
        organization_id=current_user.organization_id,
        created_by=str(current_user.id),
        scope=payload.scope,
        policy_audit_run_id=payload.policy_audit_run_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    return _serialize_brief(brief)


@router.get("/executive-briefs")
def list_executive_briefs(
    current_user: CurrentUserContext = Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            OrgScopedRepository(db, ExecutiveBrief, current_user.organization_id)
            .base_query()
            .order_by(desc(ExecutiveBrief.created_at))
            .limit(20)
        ).all()
    )
    return [_serialize_brief(b) for b in rows]


@router.get("/executive-briefs/{report_id}")
def get_executive_brief(
    report_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    brief = OrgScopedRepository(db, ExecutiveBrief, current_user.organization_id).get_by_id(
        report_id
    )
    if not brief:
        raise AppError("BRIEF_NOT_FOUND", "Executive brief not found.", status.HTTP_404_NOT_FOUND)
    return _serialize_brief(brief)


@router.get("/executive-briefs/{report_id}/download")
def download_executive_brief(
    report_id: UUID,
    format: str = Query(default="pdf", pattern="^(pdf|markdown|csv)$"),
    current_user: CurrentUserContext = Depends(require_permission("reports:download")),
    db: Session = Depends(get_db),
) -> Response:
    brief = OrgScopedRepository(db, ExecutiveBrief, current_user.organization_id).get_by_id(
        report_id
    )
    if not brief:
        raise AppError("BRIEF_NOT_FOUND", "Executive brief not found.", status.HTTP_404_NOT_FOUND)

    org = db.get(Organization, current_user.organization_id)
    org_name = org.name if org else "Organization"

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="EXECUTIVE_BRIEF_DOWNLOADED",
        entity_type="executive_brief",
        entity_id=str(brief.id),
        after={"format": format},
    )
    db.commit()

    if format == "markdown":
        md = render_brief_markdown(brief, org_name).encode("utf-8")
        return Response(
            content=md,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="executive_brief_{brief.id}.md"'
            },
        )
    if format == "csv":
        data = render_brief_csv(brief, org_name)
        return Response(
            content=data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="executive_brief_{brief.id}.csv"'
            },
        )
    pdf_bytes = render_brief_pdf(brief, org_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="executive_brief_{brief.id}.pdf"'
        },
    )
