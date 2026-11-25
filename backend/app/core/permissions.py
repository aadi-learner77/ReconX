from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import decode_token
from app.models.auth import User

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "finance_operator": {
        "transactions:read",
        "transactions:write",
        "vendors:read",
        "documents:read",
        "documents:write",
        "reconciliation:run",
        "exceptions:read",
        "exceptions:manage",
        "exceptions:comment",
        "investigations:run",
        "copilot:read",
        "reports:export",
    },
    "approver": {
        "transactions:read",
        "vendors:read",
        "documents:read",
        "exceptions:read",
        "exceptions:comment",
        "approvals:decide",
        "investigations:run",
        "copilot:read",
        "reports:export",
    },
    "procurement": {
        "transactions:read",
        "transactions:write",
        "vendors:read",
        "vendors:write",
        "documents:read",
        "exceptions:read",
        "exceptions:comment",
        "exceptions:manage",
        "copilot:read",
    },
    "receiving": {
        "transactions:read",
        "receiving:write",
        "vendors:read",
        "documents:read",
        "documents:write",
        "exceptions:read",
        "exceptions:comment",
    },
    "auditor": {
        "transactions:read",
        "vendors:read",
        "documents:read",
        "exceptions:read",
        "audit:read",
        "copilot:read",
        "reports:export",
    },
    "admin": {
        "transactions:read",
        "transactions:write",
        "receiving:write",
        "vendors:read",
        "vendors:write",
        "documents:read",
        "documents:write",
        "reconciliation:run",
        "exceptions:read",
        "exceptions:manage",
        "exceptions:comment",
        "investigations:run",
        "audit:read",
        "admin:users:read",
        "admin:users:write",
        "admin:config:read",
        "admin:config:write",
        "admin:jobs:read",
        "admin:jobs:write",
        "copilot:read",
        "reports:export",
    },
}

ALL_PERMISSIONS: set[str] = set().union(*ROLE_PERMISSIONS.values())


@dataclass(frozen=True)
class CurrentUserContext:
    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    roles: list[str]
    permissions: set[str]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUserContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            code="UNAUTHORIZED",
            message="Missing or invalid Authorization header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token, expected_type="access")
    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org_id"])

    user = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
    if not user or user.status != "ACTIVE":
        raise AppError(
            code="UNAUTHORIZED",
            message="User account not found or inactive.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    roles = [r.name for r in user.roles]
    permissions: set[str] = set()
    for r in user.roles:
        for p in r.permissions:
            permissions.add(p.code)
        permissions.update(ROLE_PERMISSIONS.get(r.name, set()))

    return CurrentUserContext(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        roles=roles,
        permissions=permissions,
    )


def require_permission(
    permission_code: str,
) -> Callable[[CurrentUserContext], CurrentUserContext]:
    def _checker(
        current_user: CurrentUserContext = Depends(get_current_user),
    ) -> CurrentUserContext:
        if permission_code not in current_user.permissions:
            raise AppError(
                code="FORBIDDEN",
                message=f"Permission '{permission_code}' is required for this operation.",
                status_code=status.HTTP_403_FORBIDDEN,
                details={"required_permission": permission_code},
            )
        return current_user

    return _checker
