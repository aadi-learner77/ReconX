from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.domain import Vendor
from app.repositories.base import OrgScopedRepository
from app.schemas.common import PaginatedResponse, paginate_params
from app.schemas.domain import VendorCreateRequest, VendorResponse
from app.services.audit.service import record_audit_event
from app.services.transactions.bundle import normalize_name, vendor_to_response

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=PaginatedResponse[VendorResponse])
def list_vendors(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("vendors:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[VendorResponse]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, Vendor, current_user.organization_id)
    stmt = repo.base_query()
    if search:
        stmt = stmt.where(Vendor.legal_name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(asc(Vendor.legal_name), asc(Vendor.id)).offset(offset).limit(safe_size)
        ).all()
    )
    return PaginatedResponse(
        items=[vendor_to_response(v) for v in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreateRequest,
    current_user: CurrentUserContext = Depends(require_permission("vendors:write")),
    db: Session = Depends(get_db),
) -> VendorResponse:
    norm = normalize_name(payload.legal_name)
    repo = OrgScopedRepository(db, Vendor, current_user.organization_id)
    existing = db.scalar(repo.base_query().where(Vendor.normalized_name == norm))
    if existing:
        raise AppError(
            code="VENDOR_EXISTS",
            message="Vendor with normalized name already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )
    vendor = Vendor(
        organization_id=current_user.organization_id,
        legal_name=payload.legal_name,
        normalized_name=norm,
        tax_identifier=payload.tax_identifier,
        bank_account_masked=payload.bank_account_masked,
        status="ACTIVE",
    )
    db.add(vendor)
    db.flush()
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="VENDOR_CREATED",
        entity_type="vendor",
        entity_id=str(vendor.id),
        after={"legal_name": vendor.legal_name},
    )
    db.commit()
    db.refresh(vendor)
    return vendor_to_response(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("vendors:read")),
    db: Session = Depends(get_db),
) -> VendorResponse:
    repo = OrgScopedRepository(db, Vendor, current_user.organization_id)
    vendor = repo.get_by_id(vendor_id)
    if not vendor:
        raise AppError("VENDOR_NOT_FOUND", "Vendor not found.", status.HTTP_404_NOT_FOUND)
    return vendor_to_response(vendor)
