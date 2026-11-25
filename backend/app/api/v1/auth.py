from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    login_rate_limiter,
    verify_password,
)
from app.models.auth import Organization, RefreshToken, User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.services.audit.service import record_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"{client_host}:{payload.email.lower()}"
    login_rate_limiter.check_and_record(
        rate_key,
        max_attempts=settings.login_rate_limit_max_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if user.status != "ACTIVE":
        raise AppError(
            code="ACCOUNT_INACTIVE",
            message="User account is inactive.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    roles = [r.name for r in user.roles]
    access_token = create_access_token(user.id, user.organization_id, roles)
    refresh_token, jti, expires_at = create_refresh_token(user.id, user.organization_id, roles)

    db.add(
        RefreshToken(
            organization_id=user.organization_id,
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            revoked=False,
        )
    )
    record_audit_event(
        db,
        organization_id=user.organization_id,
        actor_type="USER",
        actor_id=str(user.id),
        action="AUTH_LOGIN",
        entity_type="user",
        entity_id=str(user.id),
        after={"email": user.email, "roles": roles},
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_seconds=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    jti = claims["jti"]

    stored = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not stored or stored.revoked:
        raise AppError(
            code="REFRESH_TOKEN_REVOKED",
            message="Refresh token has been revoked or does not exist.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = (
        db.query(User)
        .filter(User.id == stored.user_id, User.organization_id == stored.organization_id)
        .first()
    )
    if not user or user.status != "ACTIVE":
        raise AppError(
            code="UNAUTHORIZED",
            message="User account not active.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    stored.revoked = True
    roles = [r.name for r in user.roles]
    access_token = create_access_token(user.id, user.organization_id, roles)
    new_refresh, new_jti, expires_at = create_refresh_token(user.id, user.organization_id, roles)
    db.add(
        RefreshToken(
            organization_id=user.organization_id,
            user_id=user.id,
            jti=new_jti,
            expires_at=expires_at,
            revoked=False,
        )
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in_seconds=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    payload: LogoutRequest,
    current_user: CurrentUserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if payload.refresh_token:
        try:
            claims = decode_token(payload.refresh_token, expected_type="refresh")
            stored = (
                db.query(RefreshToken)
                .filter(
                    RefreshToken.jti == claims["jti"],
                    RefreshToken.organization_id == current_user.organization_id,
                    RefreshToken.user_id == current_user.id,
                )
                .first()
            )
            if stored:
                stored.revoked = True
        except AppError:
            pass
    else:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.organization_id == current_user.organization_id,
            RefreshToken.revoked.is_(False),
        ).update({"revoked": True})

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="AUTH_LOGOUT",
        entity_type="user",
        entity_id=str(current_user.id),
    )
    db.commit()
    return {"status": "logged_out"}


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    current_user: CurrentUserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    return UserProfileResponse(
        id=current_user.id,
        organization_id=current_user.organization_id,
        organization_name=org.name if org else "",
        email=current_user.email,
        full_name=current_user.full_name,
        status="ACTIVE",
        roles=sorted(current_user.roles),
        permissions=sorted(current_user.permissions),
    )
