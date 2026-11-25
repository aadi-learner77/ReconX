from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext
from app.models.config import AppConfig
from app.models.domain import (
    Approval,
    ExceptionCase,
    Invoice,
    Notification,
    PurchaseOrder,
    RiskSignal,
)
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.workflows.state_machine import DECISION_TO_TARGET_STATE, validate_transition


def create_redacted_notification(
    db: Session,
    *,
    organization_id: UUID,
    recipient_id: UUID,
    notif_type: str,
    reference_id: str,
    message: str,
) -> Notification:
    """Create an in-app notification without leaking sensitive invoice amounts/bank numbers."""
    notif = Notification(
        organization_id=organization_id,
        recipient_id=recipient_id,
        type=notif_type,
        reference_id=reference_id,
        message=message[:450],
        status="UNREAD",
    )
    db.add(notif)
    return notif


def _get_transaction_amount_and_maker(
    db: Session, organization_id: UUID, transaction_id: UUID
) -> tuple[Decimal, UUID | None]:
    po = OrgScopedRepository(db, PurchaseOrder, organization_id).get_by_id(transaction_id)
    if po is not None:
        return po.total_amount, None
    inv = OrgScopedRepository(db, Invoice, organization_id).get_by_id(transaction_id)
    if inv is not None:
        return inv.total_amount, None
    return Decimal("0"), None


def decide_exception_case(
    db: Session,
    *,
    case_id: UUID,
    decision: str,
    rationale: str,
    expected_version: int | None,
    current_user: CurrentUserContext,
) -> dict[str, Any]:
    """Server-side approval workflow with strict ordered checks (SRS 5.8, AT-09, AT-12)."""
    # 1. Authenticated (enforced by caller dependency) & 2. Role check
    decision_upper = decision.upper().strip()
    if decision_upper not in DECISION_TO_TARGET_STATE:
        raise AppError(
            code="INVALID_DECISION",
            message=f"Unsupported decision '{decision}'.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if decision_upper in {"APPROVE", "REJECT"}:
        if "approvals:decide" not in current_user.permissions:
            raise AppError(
                code="APPROVAL_NOT_AUTHORIZED",
                message="You do not have permission to approve or reject this case.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
    else:
        if (
            "exceptions:manage" not in current_user.permissions
            and "approvals:decide" not in current_user.permissions
        ):
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission to route this case.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    case = OrgScopedRepository(db, ExceptionCase, current_user.organization_id).get_by_id(case_id)
    if not case:
        raise AppError("CASE_NOT_FOUND", "Exception case not found.", status.HTTP_404_NOT_FOUND)

    # Load active org config for approval limits & maker-checker threshold
    cfg = db.scalar(
        OrgScopedRepository(db, AppConfig, current_user.organization_id)
        .base_query()
        .where(AppConfig.is_active.is_(True))
        .order_by(desc(AppConfig.version))
    )
    cfg_json = cfg.config_json if cfg else {}
    limits_map: dict[str, str] = cfg_json.get("approval_limits", {})
    maker_checker_threshold = Decimal(str(cfg_json.get("maker_checker_threshold", "100000.00")))

    tx_amount, _ = _get_transaction_amount_and_maker(
        db, current_user.organization_id, case.transaction_id
    )

    # 3. Approval limit check (for APPROVE)
    if decision_upper == "APPROVE":
        user_max_limit = Decimal("0")
        for role_name in current_user.roles:
            role_limit = Decimal(str(limits_map.get(role_name, "0")))
            if role_limit > user_max_limit:
                user_max_limit = role_limit
        if tx_amount > user_max_limit:
            raise AppError(
                code="APPROVAL_LIMIT_EXCEEDED",
                message=(
                    f"Transaction amount {tx_amount} exceeds your role approval limit "
                    f"({user_max_limit})."
                ),
                status_code=status.HTTP_403_FORBIDDEN,
                details={"amount": str(tx_amount), "limit": str(user_max_limit)},
            )

        # 4. Maker-checker separation for high-value or high-risk cases
        high_risk = bool(
            db.scalar(
                OrgScopedRepository(db, RiskSignal, current_user.organization_id)
                .base_query()
                .where(
                    RiskSignal.transaction_id == case.transaction_id,
                    RiskSignal.severity == "HIGH",
                )
            )
        )
        is_high_value = tx_amount >= maker_checker_threshold
        if (is_high_value or high_risk or case.severity == "HIGH") and (
            case.created_by == current_user.id or case.owner_id == current_user.id
        ):
            raise AppError(
                code="MAKER_CHECKER_VIOLATION",
                message="Maker-checker policy prevents the case owner/creator from approving.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    # 5. Case state transition check
    target_state = DECISION_TO_TARGET_STATE[decision_upper]
    validate_transition(case.status, target_state)

    # 6. Optimistic-lock version check
    if expected_version is not None and case.version != expected_version:
        raise AppError(
            code="STALE_CASE_VERSION",
            message="Case was modified by another user. Please refresh before deciding.",
            status_code=status.HTTP_409_CONFLICT,
            details={"expected": expected_version, "actual": case.version},
        )

    # 7. Rationale required
    cleaned_rationale = rationale.strip()
    if len(cleaned_rationale) < 3:
        raise AppError(
            code="RATIONALE_REQUIRED",
            message="A decision rationale is required.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    before_state = {"status": case.status, "version": case.version}
    case.status = target_state
    case.version += 1

    approval = Approval(
        organization_id=current_user.organization_id,
        case_id=case.id,
        transaction_id=case.transaction_id,
        approver_id=current_user.id,
        decision=decision_upper,
        rationale=cleaned_rationale,
        amount_evaluated=tx_amount,
        decided_at=datetime.now(UTC),
    )
    db.add(approval)
    db.flush()

    # Update PO/Invoice workflow status if approved/rejected (workflow status only; NO payment!)
    if target_state in {"APPROVED", "REJECTED"}:
        po = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id).get_by_id(
            case.transaction_id
        )
        if po is not None:
            open_remaining = (
                db.query(ExceptionCase)
                .filter(
                    ExceptionCase.organization_id == current_user.organization_id,
                    ExceptionCase.transaction_id == case.transaction_id,
                    ExceptionCase.id != case.id,
                    ExceptionCase.status.notin_(["APPROVED", "REJECTED"]),
                )
                .count()
            )
            if target_state == "REJECTED":
                po.status = "REJECTED"
            elif open_remaining == 0:
                po.status = "APPROVED"

    if case.owner_id and case.owner_id != current_user.id:
        create_redacted_notification(
            db,
            organization_id=current_user.organization_id,
            recipient_id=case.owner_id,
            notif_type=f"CASE_{target_state}",
            reference_id=str(case.id),
            message=f"Exception case status updated to {target_state}.",
        )

    audit_evt = record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"CASE_DECISION_{decision_upper}",
        entity_type="exception_case",
        entity_id=str(case.id),
        before=before_state,
        after={
            "status": case.status,
            "version": case.version,
            "decision": decision_upper,
            "rationale": cleaned_rationale,
            "approval_id": str(approval.id),
        },
    )
    db.commit()

    return {
        "case_id": str(case.id),
        "status": case.status,
        "version": case.version,
        "approval_id": str(approval.id),
        "audit_event_id": str(audit_evt.id),
    }
