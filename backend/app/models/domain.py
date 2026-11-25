import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class VerificationStatus(enum.StrEnum):
    EXTRACTED = "extracted"
    USER_CORRECTED = "user_corrected"
    SYSTEM_DERIVED = "system_derived"


class Vendor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vendor"
    __table_args__ = (
        UniqueConstraint("organization_id", "normalized_name", name="uq_vendor_org_norm"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_identifier: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    bank_account_masked: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class VendorBankChange(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "vendor_bank_change"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendor.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_masked: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    new_masked: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ENHANCED_VERIFICATION_REQUIRED"
    )
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    classification_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0000")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_duplicate_file: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    raw_text_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")

    fields: Mapped[list["ExtractionField"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )


class ExtractionField(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "extraction_field"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0000")
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    evidence_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bbox_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False, default="heuristic")
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VerificationStatus.EXTRACTED.value
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    document: Mapped[Document] = relationship(back_populates="fields")


class PurchaseOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_order"
    __table_args__ = (
        UniqueConstraint("organization_id", "po_number", name="uq_po_org_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendor.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    po_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    freight_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    scenario_label: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )

    lines: Mapped[list["POLine"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )


class POLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "po_line"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchase_order.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    uom: Mapped[str] = mapped_column(String(32), nullable=False, default="EA")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.0000")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")


class GoodsReceipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "goods_receipt"
    __table_args__ = (
        UniqueConstraint("organization_id", "grn_number", name="uq_grn_org_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendor.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    grn_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    po_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("purchase_order.id", ondelete="SET NULL"), nullable=True, index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACCEPTED")
    scenario_label: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )

    lines: Mapped[list["GRNLine"]] = relationship(
        back_populates="goods_receipt", cascade="all, delete-orphan", lazy="selectin"
    )


class GRNLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "grn_line"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    grn_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("goods_receipt.id", ondelete="CASCADE"), nullable=False, index=True
    )
    po_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("po_line.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    received_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    rejected_qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    uom: Mapped[str] = mapped_column(String(32), nullable=False, default="EA")

    goods_receipt: Mapped[GoodsReceipt] = relationship(back_populates="lines")


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoice"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "vendor_id",
            "normalized_invoice_number",
            name="uq_invoice_org_vendor_norm",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendor.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    normalized_invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    po_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("purchase_order.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    freight_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    scenario_label: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    duplicate_of_invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )


class InvoiceLine(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "invoice_line"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False, index=True
    )
    po_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("po_line.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    uom: Mapped[str] = mapped_column(String(32), nullable=False, default="EA")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.0000")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class ToleranceConfig(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tolerance_config"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("vendor.id", ondelete="CASCADE"), nullable=True, index=True
    )
    item_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    price_abs_tolerance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    price_pct_tolerance: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.0200")
    )
    qty_abs_tolerance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    qty_pct_tolerance: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.0000")
    )
    tax_abs_tolerance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("1.0000")
    )
    allow_partial_billing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_service_advance_billing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_job_org_idempotency"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReconciliationRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "reconciliation_run"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    totals_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    results: Mapped[list["MatchResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", lazy="selectin"
    )


class MatchResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "match_result"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reconciliation_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_line_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_value: Mapped[str] = mapped_column(String(255), nullable=False)
    actual_value: Mapped[str] = mapped_column(String(255), nullable=False)
    variance: Mapped[str] = mapped_column(String(255), nullable=False, default="0")
    tolerance_applied: Mapped[str] = mapped_column(String(255), nullable=False, default="exact")
    breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rule_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)

    run: Mapped[ReconciliationRun] = relationship(back_populates="results")


class ExceptionCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "exception_case"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("reconciliation_run.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_fields_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    values_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rule_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    evidence_refs_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ExceptionComment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "exception_comment"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exception_case.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_clarification_request: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Investigation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "investigation"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exception_case.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    model_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    model_name: Mapped[str] = mapped_column(String(64), nullable=False, default="deterministic")
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    structured_output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0000")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class RiskSignal(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "risk_signal"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM")
    score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0000")
    )
    reason_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="rules-v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Approval(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "approval"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("exception_case.id", ondelete="CASCADE"), nullable=True, index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    approver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    amount_evaluated: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Notification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "notification"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNREAD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
