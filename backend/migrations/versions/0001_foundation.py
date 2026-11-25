"""foundation auth rbac config audit

Revision ID: 0001_foundation
Revises:
Create Date: 2026-11-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_foundation"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "role",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "permission",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255), nullable=False),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
    )
    op.create_index("ix_user_organization_id", "user", ["organization_id"])
    op.create_index("ix_user_email", "user", ["email"])

    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Uuid(), sa.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "app_config",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_app_config_organization_id", "app_config", ["organization_id"])

    op.create_table(
        "audit_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
    )
    op.create_index("ix_audit_event_organization_id", "audit_event", ["organization_id"])
    op.create_index("ix_audit_event_action", "audit_event", ["action"])
    op.create_index("ix_audit_event_entity_type", "audit_event", ["entity_type"])
    op.create_index("ix_audit_event_entity_id", "audit_event", ["entity_id"])
    op.create_index("ix_audit_event_timestamp", "audit_event", ["timestamp"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_event is append-only: % forbidden', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER audit_event_no_update_delete
            BEFORE UPDATE OR DELETE ON audit_event
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation();
            """
        )
    elif bind.dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_audit_event_update
            BEFORE UPDATE ON audit_event
            BEGIN
                SELECT RAISE(ABORT, 'audit_event is append-only: UPDATE forbidden');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_audit_event_delete
            BEFORE DELETE ON audit_event
            BEGIN
                SELECT RAISE(ABORT, 'audit_event is append-only: DELETE forbidden');
            END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_event_no_update_delete ON audit_event;")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_event_mutation();")
    elif bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_event_update;")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_event_delete;")

    op.drop_table("audit_event")
    op.drop_table("app_config")
    op.drop_table("refresh_token")
    op.drop_table("role_permission")
    op.drop_table("user_role")
    op.drop_table("user")
    op.drop_table("permission")
    op.drop_table("role")
    op.drop_table("organization")
