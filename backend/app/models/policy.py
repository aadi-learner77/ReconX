from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Policy(Base):
    __tablename__ = "policy"
    __table_args__ = (
        UniqueConstraint("organization_id", "policy_key", name="uq_policy_org_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="FINANCIAL")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    is_system_policy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class PolicyVersion(Base):
    __tablename__ = "policy_version"
    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version_num"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("policy.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyAuditRun(Base):
    __tablename__ = "policy_audit_run"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    selected_policy_versions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    transactions_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluations_performed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_exceptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    existing_exceptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved_exceptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyEvaluation(Base):
    __tablename__ = "policy_evaluation"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("policy.id", ondelete="CASCADE"), nullable=False, index=True
    )
    policy_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("policy_version.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audit_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("policy_audit_run.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reconciliation_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("reconciliation_run.id", ondelete="SET NULL"), nullable=True
    )
    transaction_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_conditions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    violation_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    exception_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("exception_case.id", ondelete="SET NULL"), nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ExecutiveBrief(Base):
    __tablename__ = "executive_brief"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reconciliation_run_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    policy_audit_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("policy_audit_run.id", ondelete="SET NULL"), nullable=True
    )
    policy_version_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    exposure_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    top_exceptions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    citations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    policy_diff_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    limitations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class LLMTelemetry(Base):
    __tablename__ = "llm_telemetry"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=True, index=True
    )
    configured_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    actual_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operation_name: Mapped[str] = mapped_column(String(64), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_category: Mapped[str] = mapped_column(String(64), nullable=False, default="NONE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class GraphOutboxEvent(Base):
    """PostgreSQL transactional outbox for reliable idempotent Neo4j synchronization."""

    __tablename__ = "graph_outbox_event"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
