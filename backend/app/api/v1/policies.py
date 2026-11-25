from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.policy import Policy, PolicyAuditRun, PolicyEvaluation, PolicyVersion
from app.repositories.base import OrgScopedRepository
from app.services.policies.dsl import ALLOWED_FIELDS, ALLOWED_OPERATORS, PolicyDefinition
from app.services.policies.engine import (
    activate_policy,
    create_policy,
    deactivate_policy,
    preview_policy_impact,
    run_policy_audit,
    update_policy_draft,
)

router = APIRouter(tags=["policies"])


class PolicyCreateRequest(BaseModel):
    policy_key: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="FINANCIAL", max_length=64)
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    definition: dict[str, Any]
    change_summary: str = Field(default="Initial draft", max_length=500)


class PolicyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=64)
    severity: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    definition: dict[str, Any] | None = None
    change_summary: str = Field(default="Updated definition", max_length=500)


class PolicyPreviewRequest(BaseModel):
    definition: dict[str, Any]
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    policy_key: str = Field(default="DRAFT_PREVIEW", max_length=64)


class PolicyAuditRequest(BaseModel):
    policy_ids: list[UUID] | None = None
    categories: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None


def _serialize_policy(
    db: Session, org_id: UUID, pol: Policy
) -> dict[str, Any]:
    versions = list(
        db.scalars(
            OrgScopedRepository(db, PolicyVersion, org_id)
            .base_query()
            .where(PolicyVersion.policy_id == pol.id)
            .order_by(desc(PolicyVersion.version_number))
        ).all()
    )
    active_ver = (
        next((v for v in versions if v.id == pol.active_version_id), None)
        if pol.active_version_id
        else None
    )
    latest_ver = versions[0] if versions else None
    chosen_ver = active_ver or latest_ver
    return {
        "id": str(pol.id),
        "policy_key": pol.policy_key,
        "name": pol.name,
        "description": pol.description,
        "category": pol.category,
        "status": pol.status,
        "severity": pol.severity,
        "is_system_policy": pol.is_system_policy,
        "active_version": active_ver.version_number if active_ver else None,
        "latest_version": latest_ver.version_number if latest_ver else 1,
        "content_hash": chosen_ver.content_hash if chosen_ver is not None else "",
        "definition": chosen_ver.definition_json if chosen_ver is not None else {},
        "created_by": pol.created_by,
        "updated_by": pol.updated_by,
        "created_at": pol.created_at.isoformat(),
        "updated_at": pol.updated_at.isoformat(),
    }


@router.get("/policies/metadata")
def get_policy_dsl_metadata(
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
) -> dict[str, Any]:
    return {
        "allowed_fields": ALLOWED_FIELDS,
        "allowed_operators": sorted(ALLOWED_OPERATORS),
        "categories": ["FINANCIAL", "PROCUREMENT", "COMPLIANCE", "VENDOR", "DUPLICATE"],
        "severities": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    }


@router.get("/policies")
def list_policies(
    category: str | None = None,
    status_filter: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org_id = current_user.organization_id
    stmt = OrgScopedRepository(db, Policy, org_id).base_query()
    if category:
        stmt = stmt.where(Policy.category == category.upper())
    if status_filter:
        stmt = stmt.where(Policy.status == status_filter.upper())
    if severity:
        stmt = stmt.where(Policy.severity == severity.upper())
    rows = list(db.scalars(stmt.order_by(desc(Policy.updated_at))).all())
    if q:
        q_low = q.lower()
        rows = [
            r
            for r in rows
            if q_low in r.name.lower() or q_low in r.policy_key.lower()
        ]
    items = [_serialize_policy(db, org_id, r) for r in rows]
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "active": sum(1 for i in items if i["status"] == "ACTIVE"),
            "inactive": sum(1 for i in items if i["status"] == "INACTIVE"),
            "draft": sum(1 for i in items if i["status"] == "DRAFT"),
        },
    }


@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy_endpoint(
    payload: PolicyCreateRequest,
    current_user: CurrentUserContext = Depends(require_permission("policies:create")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        pol, _ = create_policy(
            db,
            organization_id=current_user.organization_id,
            actor_id=str(current_user.id),
            policy_key=payload.policy_key,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            severity=payload.severity,
            definition_dict=payload.definition,
            change_summary=payload.change_summary,
        )
    except ValueError as exc:
        raise AppError(
            "INVALID_POLICY_DEFINITION", str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from exc
    return _serialize_policy(db, current_user.organization_id, pol)


@router.post("/policies/preview")
def preview_policy_endpoint(
    payload: PolicyPreviewRequest,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return preview_policy_impact(
            db,
            organization_id=current_user.organization_id,
            definition_dict=payload.definition,
            severity=payload.severity,
            policy_key=payload.policy_key,
        )
    except ValueError as exc:
        raise AppError(
            "INVALID_POLICY_DEFINITION", str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from exc


@router.get("/policies/{policy_id}")
def get_policy_endpoint(
    policy_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    pol = OrgScopedRepository(db, Policy, current_user.organization_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)
    return _serialize_policy(db, current_user.organization_id, pol)


@router.put("/policies/{policy_id}")
def update_policy_endpoint(
    policy_id: UUID,
    payload: PolicyUpdateRequest,
    current_user: CurrentUserContext = Depends(require_permission("policies:update")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        pol, _ = update_policy_draft(
            db,
            organization_id=current_user.organization_id,
            policy_id=policy_id,
            actor_id=str(current_user.id),
            name=payload.name,
            description=payload.description,
            category=payload.category,
            severity=payload.severity,
            definition_dict=payload.definition,
            change_summary=payload.change_summary,
        )
    except ValueError as exc:
        raise AppError(
            "INVALID_POLICY_DEFINITION", str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from exc
    return _serialize_policy(db, current_user.organization_id, pol)


@router.post("/policies/{policy_id}/validate")
def validate_policy_endpoint(
    policy_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    pol = OrgScopedRepository(db, Policy, current_user.organization_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)
    ver = db.scalar(
        OrgScopedRepository(db, PolicyVersion, current_user.organization_id)
        .base_query()
        .where(PolicyVersion.policy_id == pol.id)
        .order_by(desc(PolicyVersion.version_number))
    )
    if not ver:
        raise AppError("POLICY_VERSION_NOT_FOUND", "No version found.", status.HTTP_404_NOT_FOUND)
    try:
        PolicyDefinition.model_validate(ver.definition_json)
        ver.is_validated = True
        if pol.status == "DRAFT":
            pol.status = "VALIDATED"
        db.commit()
        return {"valid": True, "version_number": ver.version_number, "status": pol.status}
    except ValueError as exc:
        raise AppError(
            "INVALID_POLICY_DEFINITION", str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from exc


@router.post("/policies/{policy_id}/activate")
def activate_policy_endpoint(
    policy_id: UUID,
    version_number: int | None = None,
    current_user: CurrentUserContext = Depends(require_permission("policies:activate")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    pol, _ = activate_policy(
        db,
        organization_id=current_user.organization_id,
        policy_id=policy_id,
        actor_id=str(current_user.id),
        version_number=version_number,
    )
    return _serialize_policy(db, current_user.organization_id, pol)


@router.post("/policies/{policy_id}/deactivate")
def deactivate_policy_endpoint(
    policy_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:activate")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    pol = deactivate_policy(
        db,
        organization_id=current_user.organization_id,
        policy_id=policy_id,
        actor_id=str(current_user.id),
    )
    return _serialize_policy(db, current_user.organization_id, pol)


@router.post("/policies/{policy_id}/clone", status_code=status.HTTP_201_CREATED)
def clone_policy_endpoint(
    policy_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:create")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org_id = current_user.organization_id
    src = OrgScopedRepository(db, Policy, org_id).get_by_id(policy_id)
    if not src:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)
    ver = db.scalar(
        OrgScopedRepository(db, PolicyVersion, org_id)
        .base_query()
        .where(PolicyVersion.policy_id == src.id)
        .order_by(desc(PolicyVersion.version_number))
    )
    if not ver:
        raise AppError("POLICY_VERSION_NOT_FOUND", "No version found.", status.HTTP_404_NOT_FOUND)
    clone_key = f"{src.policy_key}-COPY-{str(src.id)[:4].upper()}"
    pol, _ = create_policy(
        db,
        organization_id=org_id,
        actor_id=str(current_user.id),
        policy_key=clone_key,
        name=f"{src.name} (Copy)",
        description=src.description,
        category=src.category,
        severity=src.severity,
        definition_dict=ver.definition_json,
        change_summary=f"Cloned from {src.policy_key} v{ver.version_number}",
    )
    return _serialize_policy(db, org_id, pol)


@router.get("/policies/{policy_id}/versions")
def list_policy_versions(
    policy_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    org_id = current_user.organization_id
    pol = OrgScopedRepository(db, Policy, org_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)
    vers = list(
        db.scalars(
            OrgScopedRepository(db, PolicyVersion, org_id)
            .base_query()
            .where(PolicyVersion.policy_id == pol.id)
            .order_by(desc(PolicyVersion.version_number))
        ).all()
    )
    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "content_hash": v.content_hash,
            "change_summary": v.change_summary,
            "is_active": v.id == pol.active_version_id,
            "definition": v.definition_json,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat(),
            "activated_at": v.activated_at.isoformat() if v.activated_at else None,
        }
        for v in vers
    ]


@router.get("/policies/{policy_id}/evaluations")
def list_policy_evaluations(
    policy_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    org_id = current_user.organization_id
    pol = OrgScopedRepository(db, Policy, org_id).get_by_id(policy_id)
    if not pol:
        raise AppError("POLICY_NOT_FOUND", "Policy not found.", status.HTTP_404_NOT_FOUND)
    evals = list(
        db.scalars(
            OrgScopedRepository(db, PolicyEvaluation, org_id)
            .base_query()
            .where(PolicyEvaluation.policy_id == pol.id)
            .order_by(desc(PolicyEvaluation.evaluated_at))
            .limit(50)
        ).all()
    )
    return [
        {
            "id": str(e.id),
            "policy_version_id": str(e.policy_version_id),
            "transaction_id": str(e.transaction_id),
            "status": e.status,
            "result_summary": e.result_summary,
            "exception_id": str(e.exception_id) if e.exception_id else None,
            "evaluated_at": e.evaluated_at.isoformat(),
        }
        for e in evals
    ]


@router.post("/policy-audits", status_code=status.HTTP_201_CREATED)
def start_policy_audit(
    payload: PolicyAuditRequest,
    current_user: CurrentUserContext = Depends(require_permission("policies:audit")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run = run_policy_audit(
        db,
        organization_id=current_user.organization_id,
        triggered_by=str(current_user.id),
        policy_ids=payload.policy_ids,
        categories=payload.categories,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    return _serialize_audit_run(run)


@router.get("/policy-audits")
def list_policy_audits(
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    runs = list(
        db.scalars(
            OrgScopedRepository(db, PolicyAuditRun, current_user.organization_id)
            .base_query()
            .order_by(desc(PolicyAuditRun.started_at))
            .limit(25)
        ).all()
    )
    return [_serialize_audit_run(r) for r in runs]


@router.get("/policy-audits/{audit_run_id}")
def get_policy_audit(
    audit_run_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run = OrgScopedRepository(db, PolicyAuditRun, current_user.organization_id).get_by_id(
        audit_run_id
    )
    if not run:
        raise AppError(
            "AUDIT_RUN_NOT_FOUND", "Policy audit run not found.", status.HTTP_404_NOT_FOUND
        )
    return _serialize_audit_run(run)


@router.get("/policy-audits/{audit_run_id}/results")
def get_policy_audit_results(
    audit_run_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run = OrgScopedRepository(db, PolicyAuditRun, current_user.organization_id).get_by_id(
        audit_run_id
    )
    if not run:
        raise AppError(
            "AUDIT_RUN_NOT_FOUND", "Policy audit run not found.", status.HTTP_404_NOT_FOUND
        )
    return {
        "audit_run_id": str(run.id),
        "status": run.status,
        "selected_policy_versions": run.selected_policy_versions_json,
        **(run.summary_json or {}),
    }


@router.post("/policy-audits/{audit_run_id}/retry", status_code=status.HTTP_201_CREATED)
def retry_policy_audit(
    audit_run_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("policies:audit")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    old = OrgScopedRepository(db, PolicyAuditRun, current_user.organization_id).get_by_id(
        audit_run_id
    )
    if not old:
        raise AppError(
            "AUDIT_RUN_NOT_FOUND", "Policy audit run not found.", status.HTTP_404_NOT_FOUND
        )
    scope = old.scope_json or {}
    pids = [UUID(x) for x in scope.get("policy_ids", [])] or None
    cats = scope.get("categories") or None
    new_run = run_policy_audit(
        db,
        organization_id=current_user.organization_id,
        triggered_by=str(current_user.id),
        policy_ids=pids,
        categories=cats,
    )
    return _serialize_audit_run(new_run)


def _serialize_audit_run(r: PolicyAuditRun) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "triggered_by": r.triggered_by,
        "status": r.status,
        "selected_policy_versions": r.selected_policy_versions_json,
        "transactions_scanned": r.transactions_scanned,
        "evaluations_performed": r.evaluations_performed,
        "new_exceptions": r.new_exceptions,
        "existing_exceptions": r.existing_exceptions,
        "resolved_exceptions": r.resolved_exceptions,
        "error_count": r.error_count,
        "summary": r.summary_json,
        "started_at": r.started_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }
