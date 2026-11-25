from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import CurrentUserContext, require_permission
from app.models.audit import AuditEvent
from app.repositories.base import OrgScopedRepository
from app.schemas.audit import AuditEventResponse
from app.schemas.common import PaginatedResponse, paginate_params

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditEventResponse])
def list_audit_events(
    actor_id: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    current_user: CurrentUserContext = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AuditEventResponse]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, AuditEvent, current_user.organization_id)
    stmt = repo.base_query()
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if date_from:
        stmt = stmt.where(AuditEvent.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(AuditEvent.timestamp <= date_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = asc(AuditEvent.timestamp) if sort_dir == "asc" else desc(AuditEvent.timestamp)
    rows = list(
        db.scalars(stmt.order_by(order, asc(AuditEvent.id)).offset(offset).limit(safe_size)).all()
    )

    return PaginatedResponse(
        items=[
            AuditEventResponse(
                id=r.id,
                organization_id=r.organization_id,
                actor_type=r.actor_type,
                actor_id=r.actor_id,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                before_json=r.before_json,
                after_json=r.after_json,
                timestamp=r.timestamp,
                correlation_id=r.correlation_id,
            )
            for r in rows
        ],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )
