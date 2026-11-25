from collections import defaultdict
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import status

from app.core.config import get_settings
from app.core.exceptions import AppError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_token(
    subject: str,
    organization_id: str,
    roles: list[str],
    token_type: str,
    expires_delta: timedelta,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + expires_delta
    token_jti = jti or str(uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": organization_id,
        "roles": roles,
        "type": token_type,
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded, token_jti, exp


def create_access_token(user_id: UUID, organization_id: UUID, roles: list[str]) -> str:
    settings = get_settings()
    token, _, _ = create_token(
        subject=str(user_id),
        organization_id=str(organization_id),
        roles=roles,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return token


def create_refresh_token(
    user_id: UUID, organization_id: UUID, roles: list[str]
) -> tuple[str, str, datetime]:
    settings = get_settings()
    return create_token(
        subject=str(user_id),
        organization_id=str(organization_id),
        roles=roles,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            code="TOKEN_EXPIRED",
            message="Authentication token has expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc
    except jwt.PyJWTError as exc:
        raise AppError(
            code="INVALID_TOKEN",
            message="Invalid authentication token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    if expected_type and payload.get("type") != expected_type:
        raise AppError(
            code="INVALID_TOKEN_TYPE",
            message="Unexpected token type.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return payload


class LoginRateLimiter:
    """In-memory sliding-window login rate limiter keyed by client IP + email."""

    def __init__(self) -> None:
        self._attempts: dict[str, list[datetime]] = defaultdict(list)
        self._lock = Lock()

    def check_and_record(self, key: str, max_attempts: int, window_seconds: int) -> None:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)
        with self._lock:
            recent = [ts for ts in self._attempts[key] if ts > cutoff]
            if len(recent) >= max_attempts:
                self._attempts[key] = recent
                raise AppError(
                    code="LOGIN_RATE_LIMITED",
                    message="Too many login attempts. Please try again later.",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            recent.append(now)
            self._attempts[key] = recent

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._attempts.clear()
            else:
                self._attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()
