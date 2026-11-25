from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.core.security import hash_password
from app.models.auth import Role, User
from app.models.config import AppConfig
from app.models.domain import Job, ToleranceConfig
from app.repositories.base import OrgScopedRepository
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminUpdateRolesRequest,
    AdminUserResponse,
    AppConfigResponse,
    AppConfigUpdateRequest,
)
from app.schemas.common import PaginatedResponse, paginate_params
from app.schemas.domain import ToleranceConfigRequest, ToleranceConfigResponse
from app.services.audit.service import record_audit_event

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        roles=sorted([r.name for r in user.roles]),
        created_at=user.created_at,
    )


@router.get("/users", response_model=PaginatedResponse[AdminUserResponse])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    current_user: CurrentUserContext = Depends(require_permission("admin:users:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminUserResponse]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, User, current_user.organization_id)
    base = repo.base_query()
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    order = asc(User.created_at) if sort_dir == "asc" else desc(User.created_at)
    rows = list(
        db.scalars(base.order_by(order, asc(User.id)).offset(offset).limit(safe_size)).all()
    )
    return PaginatedResponse(
        items=[_to_user_response(u) for u in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    current_user: CurrentUserContext = Depends(require_permission("admin:users:write")),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    repo = OrgScopedRepository(db, User, current_user.organization_id)
    existing = db.scalar(repo.base_query().where(User.email == payload.email.lower()))
    if existing:
        raise AppError(
            code="USER_ALREADY_EXISTS",
            message="A user with this email already exists in the organization.",
            status_code=status.HTTP_409_CONFLICT,
        )

    roles = list(db.scalars(select(Role).where(Role.name.in_(payload.roles))).all())
    found_names = {r.name for r in roles}
    missing = [name for name in payload.roles if name not in found_names]
    if missing:
        raise AppError(
            code="INVALID_ROLE",
            message=f"Unknown roles: {', '.join(missing)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = User(
        organization_id=current_user.organization_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        status="ACTIVE",
        roles=roles,
    )
    db.add(user)
    db.flush()

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        after={"email": user.email, "roles": sorted(found_names)},
    )
    db.commit()
    db.refresh(user)
    return _to_user_response(user)


@router.patch("/users/{user_id}/roles", response_model=AdminUserResponse)
def update_user_roles(
    user_id: UUID,
    payload: AdminUpdateRolesRequest,
    current_user: CurrentUserContext = Depends(require_permission("admin:users:write")),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    repo = OrgScopedRepository(db, User, current_user.organization_id)
    user = repo.get_by_id(user_id)
    if not user:
        raise AppError(
            code="USER_NOT_FOUND",
            message="User not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    roles = list(db.scalars(select(Role).where(Role.name.in_(payload.roles))).all())
    found_names = {r.name for r in roles}
    missing = [name for name in payload.roles if name not in found_names]
    if missing:
        raise AppError(
            code="INVALID_ROLE",
            message=f"Unknown roles: {', '.join(missing)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    before_roles = sorted([r.name for r in user.roles])
    user.roles = roles
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="USER_ROLES_UPDATED",
        entity_type="user",
        entity_id=str(user.id),
        before={"roles": before_roles},
        after={"roles": sorted(found_names)},
    )
    db.commit()
    db.refresh(user)
    return _to_user_response(user)


@router.get("/config", response_model=AppConfigResponse)
def get_active_config(
    current_user: CurrentUserContext = Depends(require_permission("admin:config:read")),
    db: Session = Depends(get_db),
) -> AppConfigResponse:
    repo = OrgScopedRepository(db, AppConfig, current_user.organization_id)
    cfg = db.scalar(
        repo.base_query()
        .where(AppConfig.is_active.is_(True))
        .order_by(desc(AppConfig.version))
    )
    if not cfg:
        raise AppError(
            code="CONFIG_NOT_FOUND",
            message="Active organization configuration not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return AppConfigResponse(
        id=cfg.id,
        organization_id=cfg.organization_id,
        version=cfg.version,
        is_active=cfg.is_active,
        config_json=cfg.config_json,
        updated_by=cfg.updated_by,
        created_at=cfg.created_at,
    )


@router.put("/config", response_model=AppConfigResponse)
def update_config(
    payload: AppConfigUpdateRequest,
    current_user: CurrentUserContext = Depends(require_permission("admin:config:write")),
    db: Session = Depends(get_db),
) -> AppConfigResponse:
    repo = OrgScopedRepository(db, AppConfig, current_user.organization_id)
    current = db.scalar(
        repo.base_query()
        .where(AppConfig.is_active.is_(True))
        .order_by(desc(AppConfig.version))
    )
    before_json = current.config_json if current else None
    next_version = (current.version + 1) if current else 1
    if current:
        current.is_active = False

    new_cfg = AppConfig(
        organization_id=current_user.organization_id,
        version=next_version,
        is_active=True,
        config_json=payload.config_json,
        updated_by=str(current_user.id),
    )
    db.add(new_cfg)
    db.flush()

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CONFIG_UPDATED",
        entity_type="app_config",
        entity_id=str(new_cfg.id),
        before=before_json,
        after=payload.config_json,
    )
    db.commit()
    db.refresh(new_cfg)
    return AppConfigResponse(
        id=new_cfg.id,
        organization_id=new_cfg.organization_id,
        version=new_cfg.version,
        is_active=new_cfg.is_active,
        config_json=new_cfg.config_json,
        updated_by=new_cfg.updated_by,
        created_at=new_cfg.created_at,
    )


def _tol_response(tol: ToleranceConfig) -> ToleranceConfigResponse:
    return ToleranceConfigResponse(
        id=tol.id,
        organization_id=tol.organization_id,
        vendor_id=tol.vendor_id,
        item_code=tol.item_code,
        price_abs_tolerance=tol.price_abs_tolerance,
        price_pct_tolerance=tol.price_pct_tolerance,
        qty_abs_tolerance=tol.qty_abs_tolerance,
        qty_pct_tolerance=tol.qty_pct_tolerance,
        tax_abs_tolerance=tol.tax_abs_tolerance,
        allow_partial_billing=tol.allow_partial_billing,
        allow_service_advance_billing=tol.allow_service_advance_billing,
        version=tol.version,
        is_active=tol.is_active,
        updated_by=tol.updated_by,
        created_at=tol.created_at,
    )


@router.get("/tolerances", response_model=list[ToleranceConfigResponse])
def list_tolerances(
    current_user: CurrentUserContext = Depends(require_permission("admin:config:read")),
    db: Session = Depends(get_db),
) -> list[ToleranceConfigResponse]:
    repo = OrgScopedRepository(db, ToleranceConfig, current_user.organization_id)
    rows = list(
        db.scalars(
            repo.base_query()
            .where(ToleranceConfig.is_active.is_(True))
            .order_by(desc(ToleranceConfig.created_at))
        ).all()
    )
    return [_tol_response(r) for r in rows]


@router.post(
    "/tolerances",
    response_model=ToleranceConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_tolerance(
    payload: ToleranceConfigRequest,
    current_user: CurrentUserContext = Depends(require_permission("admin:config:write")),
    db: Session = Depends(get_db),
) -> ToleranceConfigResponse:
    repo = OrgScopedRepository(db, ToleranceConfig, current_user.organization_id)
    stmt = repo.base_query().where(ToleranceConfig.is_active.is_(True))
    if payload.vendor_id is None:
        stmt = stmt.where(ToleranceConfig.vendor_id.is_(None))
    else:
        stmt = stmt.where(ToleranceConfig.vendor_id == payload.vendor_id)
    if payload.item_code is None:
        stmt = stmt.where(ToleranceConfig.item_code.is_(None))
    else:
        stmt = stmt.where(ToleranceConfig.item_code == payload.item_code)

    prev = db.scalar(stmt.order_by(desc(ToleranceConfig.version)))
    before = (
        {
            "price_abs": str(prev.price_abs_tolerance),
            "price_pct": str(prev.price_pct_tolerance),
            "qty_abs": str(prev.qty_abs_tolerance),
            "qty_pct": str(prev.qty_pct_tolerance),
        }
        if prev
        else None
    )
    next_ver = (prev.version + 1) if prev else 1
    if prev:
        prev.is_active = False

    tol = ToleranceConfig(
        organization_id=current_user.organization_id,
        vendor_id=payload.vendor_id,
        item_code=payload.item_code,
        price_abs_tolerance=payload.price_abs_tolerance,
        price_pct_tolerance=payload.price_pct_tolerance,
        qty_abs_tolerance=payload.qty_abs_tolerance,
        qty_pct_tolerance=payload.qty_pct_tolerance,
        tax_abs_tolerance=payload.tax_abs_tolerance,
        allow_partial_billing=payload.allow_partial_billing,
        allow_service_advance_billing=payload.allow_service_advance_billing,
        version=next_ver,
        is_active=True,
        updated_by=str(current_user.id),
    )
    db.add(tol)
    db.flush()
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="TOLERANCE_UPDATED",
        entity_type="tolerance_config",
        entity_id=str(tol.id),
        before=before,
        after={
            "price_abs": str(tol.price_abs_tolerance),
            "price_pct": str(tol.price_pct_tolerance),
            "qty_abs": str(tol.qty_abs_tolerance),
            "qty_pct": str(tol.qty_pct_tolerance),
            "version": tol.version,
        },
    )
    db.commit()
    db.refresh(tol)
    return _tol_response(tol)


@router.get("/jobs")
def list_admin_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("admin:jobs:read")),
    db: Session = Depends(get_db),
) -> dict:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, Job, current_user.organization_id)
    stmt = repo.base_query()
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(stmt.order_by(desc(Job.created_at)).offset(offset).limit(safe_size)).all()
    )
    return {
        "items": [
            {
                "job_id": str(j.id),
                "job_type": j.job_type,
                "entity_type": j.entity_type,
                "entity_id": j.entity_id,
                "status": j.status,
                "attempts": j.attempts,
                "max_attempts": j.max_attempts,
                "last_error": j.last_error,
                "created_at": j.created_at.isoformat(),
            }
            for j in rows
        ],
        "total": total,
        "page": safe_page,
        "page_size": safe_size,
        "total_pages": max(1, ceil(total / safe_size)) if total else 1,
    }


@router.post("/jobs/{job_id}/retry")
def retry_failed_job(
    job_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("admin:jobs:write")),
    db: Session = Depends(get_db),
) -> dict:
    job = OrgScopedRepository(db, Job, current_user.organization_id).get_by_id(job_id)
    if not job:
        raise AppError("JOB_NOT_FOUND", "Job not found.", status.HTTP_404_NOT_FOUND)
    if job.status != "FAILED":
        raise AppError(
            "JOB_NOT_RETRYABLE",
            f"Only FAILED jobs can be manually retried (current status: {job.status}).",
            status.HTTP_400_BAD_REQUEST,
        )
    job.status = "QUEUED"
    job.attempts = 0
    job.last_error = None
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="JOB_MANUAL_RETRY",
        entity_type="job",
        entity_id=str(job.id),
    )
    db.commit()
    return {"job_id": str(job.id), "status": job.status}
