import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    settings_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_user_org_email"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_role", back_populates="users", lazy="selectin"
    )


class Role(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "role"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    users: Mapped[list[User]] = relationship(
        secondary="user_role", back_populates="roles", lazy="selectin"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permission", back_populates="roles", lazy="selectin"
    )


class Permission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "permission"

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    roles: Mapped[list[Role]] = relationship(
        secondary="role_permission", back_populates="permissions", lazy="selectin"
    )


class UserRole(Base):
    __tablename__ = "user_role"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )


class RolePermission(Base):
    __tablename__ = "role_permission"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "refresh_token"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
