from fastapi import status

from app.core.exceptions import AppError

CASE_STATES = {"OPEN", "IN_REVIEW", "INFO_REQUESTED", "ESCALATED", "APPROVED", "REJECTED"}
TERMINAL_STATES = {"APPROVED", "REJECTED"}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"IN_REVIEW", "INFO_REQUESTED", "ESCALATED", "APPROVED", "REJECTED"},
    "IN_REVIEW": {"INFO_REQUESTED", "ESCALATED", "APPROVED", "REJECTED"},
    "INFO_REQUESTED": {"IN_REVIEW", "ESCALATED", "APPROVED", "REJECTED"},
    "ESCALATED": {"IN_REVIEW", "APPROVED", "REJECTED"},
    "APPROVED": set(),
    "REJECTED": set(),
}

DECISION_TO_TARGET_STATE: dict[str, str] = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "REQUEST_INFO": "INFO_REQUESTED",
    "ESCALATE": "ESCALATED",
}


def validate_transition(current_state: str, target_state: str) -> str:
    if target_state not in CASE_STATES:
        raise AppError(
            code="INVALID_TARGET_STATE",
            message=f"Unknown state '{target_state}'.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    if target_state not in allowed:
        raise AppError(
            code="ILLEGAL_STATE_TRANSITION",
            message=f"Cannot transition case from '{current_state}' to '{target_state}'.",
            status_code=status.HTTP_409_CONFLICT,
            details={"current_state": current_state, "target_state": target_state},
        )
    return target_state
