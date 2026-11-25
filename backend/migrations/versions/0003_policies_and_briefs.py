"""policy engine, audit runs, and executive briefs

Revision ID: 0003_policies_and_briefs
Revises: 0002_domain_entities
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_policies_and_briefs"
down_revision: str | Sequence[str] | None = "0002_domain_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("policy_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("is_system_policy", sa.Boolean(), nullable=False),
        sa.Column("active_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "policy_key", name="uq_policy_org_key"),
    )
    op.create_index("ix_policy_organization_id", "policy", ["organization_id"])

    op.create_table(
        "policy_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "policy_id", sa.Uuid(), sa.ForeignKey("policy.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("is_validated", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("policy_id", "version_number", name="uq_policy_version_num"),
    )
    op.create_index("ix_policy_version_policy_id", "policy_version", ["policy_id"])
    op.create_index("ix_policy_version_organization_id", "policy_version", ["organization_id"])

    op.create_table(
        "policy_audit_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("triggered_by", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("selected_policy_versions_json", sa.JSON(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("transactions_scanned", sa.Integer(), nullable=False),
        sa.Column("evaluations_performed", sa.Integer(), nullable=False),
        sa.Column("new_exceptions", sa.Integer(), nullable=False),
        sa.Column("existing_exceptions", sa.Integer(), nullable=False),
        sa.Column("resolved_exceptions", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_policy_audit_run_organization_id", "policy_audit_run", ["organization_id"])

    op.create_table(
        "policy_evaluation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "policy_id", sa.Uuid(), sa.ForeignKey("policy.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "policy_version_id",
            sa.Uuid(),
            sa.ForeignKey("policy_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "audit_run_id",
            sa.Uuid(),
            sa.ForeignKey("policy_audit_run.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reconciliation_run_id",
            sa.Uuid(),
            sa.ForeignKey("reconciliation_run.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("matched_conditions_json", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("violation_fingerprint", sa.String(length=128), nullable=False),
        sa.Column(
            "exception_id",
            sa.Uuid(),
            sa.ForeignKey("exception_case.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_policy_evaluation_organization_id", "policy_evaluation", ["organization_id"]
    )
    op.create_index("ix_policy_evaluation_transaction_id", "policy_evaluation", ["transaction_id"])
    op.create_index(
        "ix_policy_evaluation_violation_fingerprint",
        "policy_evaluation",
        ["violation_fingerprint"],
    )

    op.create_table(
        "executive_brief",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("scope_params_json", sa.JSON(), nullable=False),
        sa.Column("reconciliation_run_ids_json", sa.JSON(), nullable=False),
        sa.Column(
            "policy_audit_run_id",
            sa.Uuid(),
            sa.ForeignKey("policy_audit_run.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("policy_version_ids_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("exposure_json", sa.JSON(), nullable=False),
        sa.Column("top_exceptions_json", sa.JSON(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("policy_diff_json", sa.JSON(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_executive_brief_organization_id", "executive_brief", ["organization_id"])


def downgrade() -> None:
    op.drop_table("executive_brief")
    op.drop_table("policy_evaluation")
    op.drop_table("policy_audit_run")
    op.drop_table("policy_version")
    op.drop_table("policy")
