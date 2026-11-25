"""domain entities and tolerance config

Revision ID: 0002_domain_entities
Revises: 0001_foundation
Create Date: 2026-11-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_domain_entities"
down_revision: Union[str, Sequence[str], None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendor",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("tax_identifier", sa.String(length=64), nullable=False),
        sa.Column("bank_account_masked", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "normalized_name", name="uq_vendor_org_norm"),
    )
    op.create_index("ix_vendor_organization_id", "vendor", ["organization_id"])

    op.create_table(
        "vendor_bank_change",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendor.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_masked", sa.String(length=64), nullable=False),
        sa.Column("new_masked", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("verified_by", sa.String(length=128), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("classification_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("is_duplicate_file", sa.Boolean(), nullable=False),
        sa.Column("duplicate_of_document_id", sa.Uuid(), nullable=True),
        sa.Column("raw_text_excerpt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_organization_id", "document", ["organization_id"])
    op.create_index("ix_document_checksum", "document", ["checksum"])

    op.create_table(
        "extraction_field",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("evidence_ref", sa.String(length=255), nullable=False),
        sa.Column("bbox_json", sa.JSON(), nullable=True),
        sa.Column("extraction_method", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("corrected_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "purchase_order",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendor.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("po_number", sa.String(length=64), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("freight_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("scenario_label", sa.String(length=64), nullable=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "po_number", name="uq_po_org_number"),
    )

    op.create_table(
        "po_line",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("po_id", sa.Uuid(), sa.ForeignKey("purchase_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("uom", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
    )

    op.create_table(
        "goods_receipt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendor.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("grn_number", sa.String(length=64), nullable=False),
        sa.Column("po_id", sa.Uuid(), sa.ForeignKey("purchase_order.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scenario_label", sa.String(length=64), nullable=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "grn_number", name="uq_grn_org_number"),
    )

    op.create_table(
        "grn_line",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grn_id", sa.Uuid(), sa.ForeignKey("goods_receipt.id", ondelete="CASCADE"), nullable=False),
        sa.Column("po_line_id", sa.Uuid(), sa.ForeignKey("po_line.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("received_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("accepted_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("rejected_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "invoice",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendor.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_number", sa.String(length=64), nullable=False),
        sa.Column("normalized_invoice_number", sa.String(length=64), nullable=False),
        sa.Column("po_id", sa.Uuid(), sa.ForeignKey("purchase_order.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("freight_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scenario_label", sa.String(length=64), nullable=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("document.id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("duplicate_of_invoice_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "vendor_id", "normalized_invoice_number", name="uq_invoice_org_vendor_norm"),
    )

    op.create_table(
        "invoice_line",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("po_line_id", sa.Uuid(), sa.ForeignKey("po_line.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("uom", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
    )

    op.create_table(
        "tolerance_config",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendor.id", ondelete="CASCADE"), nullable=True),
        sa.Column("item_code", sa.String(length=64), nullable=True),
        sa.Column("price_abs_tolerance", sa.Numeric(18, 4), nullable=False),
        sa.Column("price_pct_tolerance", sa.Numeric(8, 4), nullable=False),
        sa.Column("qty_abs_tolerance", sa.Numeric(18, 4), nullable=False),
        sa.Column("qty_pct_tolerance", sa.Numeric(8, 4), nullable=False),
        sa.Column("tax_abs_tolerance", sa.Numeric(18, 4), nullable=False),
        sa.Column("allow_partial_billing", sa.Boolean(), nullable=False),
        sa.Column("allow_service_advance_billing", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "job",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_job_org_idempotency"),
    )

    op.create_table(
        "reconciliation_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("totals_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "match_result",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("reconciliation_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_line_id", sa.String(length=128), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("expected_value", sa.String(length=255), nullable=False),
        sa.Column("actual_value", sa.String(length=255), nullable=False),
        sa.Column("variance", sa.String(length=255), nullable=False),
        sa.Column("tolerance_applied", sa.String(length=255), nullable=False),
        sa.Column("breakdown_json", sa.JSON(), nullable=False),
        sa.Column("rule_id", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "exception_case",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("reconciliation_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("affected_fields_json", sa.JSON(), nullable=False),
        sa.Column("values_json", sa.JSON(), nullable=False),
        sa.Column("rule_id", sa.String(length=32), nullable=False),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "exception_comment",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("exception_case.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_clarification_request", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "investigation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("exception_case.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_version", sa.String(length=32), nullable=False),
        sa.Column("model_provider", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("structured_output_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "risk_signal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("reason_json", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "approval",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("exception_case.id", ondelete="CASCADE"), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("approver_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("amount_evaluated", sa.Numeric(18, 4), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "notification",
        "approval",
        "risk_signal",
        "investigation",
        "exception_comment",
        "exception_case",
        "match_result",
        "reconciliation_run",
        "job",
        "tolerance_config",
        "invoice_line",
        "invoice",
        "grn_line",
        "goods_receipt",
        "po_line",
        "purchase_order",
        "extraction_field",
        "document",
        "vendor_bank_change",
        "vendor",
    ]:
        op.drop_table(table)
