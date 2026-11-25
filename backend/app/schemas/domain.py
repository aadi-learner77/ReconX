from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class VendorCreateRequest(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    tax_identifier: str = ""
    bank_account_masked: str = ""


class VendorResponse(BaseModel):
    id: UUID
    organization_id: UUID
    legal_name: str
    normalized_name: str
    tax_identifier: str
    bank_account_masked: str
    status: str
    created_at: datetime


class POLineCreate(BaseModel):
    line_number: int = Field(ge=1)
    item_code: str = ""
    description: str = Field(min_length=1)
    uom: str = "EA"
    quantity: Decimal = Field(gt=Decimal("0"))
    unit_price: Decimal = Field(ge=Decimal("0"))
    tax_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    line_total: Decimal | None = None


class POLineResponse(BaseModel):
    id: UUID
    line_number: int
    item_code: str
    description: str
    uom: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


class PurchaseOrderCreateRequest(BaseModel):
    vendor_id: UUID
    po_number: str = Field(min_length=1, max_length=64)
    issue_date: date
    currency: str = Field(min_length=3, max_length=3, default="INR")
    freight_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    scenario_label: str | None = None
    lines: list[POLineCreate] = Field(min_length=1)


class PurchaseOrderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    vendor_id: UUID
    po_number: str
    issue_date: date
    currency: str
    status: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    freight_amount: Decimal
    total_amount: Decimal
    scenario_label: str | None
    lines: list[POLineResponse]


class GRNLineCreate(BaseModel):
    po_line_id: UUID | None = None
    item_code: str = ""
    description: str = ""
    received_qty: Decimal = Field(ge=Decimal("0"))
    accepted_qty: Decimal = Field(ge=Decimal("0"))
    rejected_qty: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    uom: str = "EA"


class GRNLineResponse(BaseModel):
    id: UUID
    po_line_id: UUID | None
    item_code: str
    description: str
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    uom: str


class GoodsReceiptCreateRequest(BaseModel):
    vendor_id: UUID
    grn_number: str = Field(min_length=1, max_length=64)
    po_id: UUID | None = None
    received_at: datetime
    scenario_label: str | None = None
    lines: list[GRNLineCreate] = Field(min_length=1)


class GoodsReceiptResponse(BaseModel):
    id: UUID
    organization_id: UUID
    vendor_id: UUID
    grn_number: str
    po_id: UUID | None
    received_at: datetime
    status: str
    scenario_label: str | None
    lines: list[GRNLineResponse]


class InvoiceLineCreate(BaseModel):
    po_line_id: UUID | None = None
    item_code: str = ""
    description: str = Field(min_length=1)
    uom: str = "EA"
    quantity: Decimal = Field(gt=Decimal("0"))
    unit_price: Decimal = Field(ge=Decimal("0"))
    tax_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    line_total: Decimal | None = None


class InvoiceLineResponse(BaseModel):
    id: UUID
    po_line_id: UUID | None
    item_code: str
    description: str
    uom: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


class InvoiceCreateRequest(BaseModel):
    vendor_id: UUID
    invoice_number: str = Field(min_length=1, max_length=64)
    po_id: UUID | None = None
    invoice_date: date
    due_date: date
    currency: str = Field(min_length=3, max_length=3, default="INR")
    freight_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    subtotal_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    scenario_label: str | None = None
    idempotency_key: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)


class InvoiceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    vendor_id: UUID
    invoice_number: str
    normalized_invoice_number: str
    po_id: UUID | None
    invoice_date: date
    due_date: date
    currency: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    freight_amount: Decimal
    total_amount: Decimal
    status: str
    scenario_label: str | None
    duplicate_of_invoice_id: UUID | None
    lines: list[InvoiceLineResponse]


class ToleranceConfigRequest(BaseModel):
    vendor_id: UUID | None = None
    item_code: str | None = None
    price_abs_tolerance: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    price_pct_tolerance: Decimal = Field(default=Decimal("0.02"), ge=Decimal("0"))
    qty_abs_tolerance: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    qty_pct_tolerance: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    tax_abs_tolerance: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0"))
    allow_partial_billing: bool = True
    allow_service_advance_billing: bool = False


class ToleranceConfigResponse(BaseModel):
    id: UUID
    organization_id: UUID
    vendor_id: UUID | None
    item_code: str | None
    price_abs_tolerance: Decimal
    price_pct_tolerance: Decimal
    qty_abs_tolerance: Decimal
    qty_pct_tolerance: Decimal
    tax_abs_tolerance: Decimal
    allow_partial_billing: bool
    allow_service_advance_billing: bool
    version: int
    is_active: bool
    updated_by: str
    created_at: datetime


class TransactionListItem(BaseModel):
    transaction_id: UUID
    transaction_type: str  # PO_BUNDLE | STANDALONE_INVOICE
    po_number: str | None
    vendor_id: UUID
    vendor_name: str
    currency: str
    total_amount: Decimal
    document_date: date
    status: str
    latest_outcome: str | None
    exception_count: int
    risk_level: str
    scenario_label: str | None


class TransactionBundleResponse(BaseModel):
    transaction_id: UUID
    organization_id: UUID
    vendor: VendorResponse
    purchase_order: PurchaseOrderResponse | None
    goods_receipts: list[GoodsReceiptResponse]
    invoices: list[InvoiceResponse]
    current_status: str
    latest_reconciliation: dict[str, Any] | None = None
    exceptions: list[dict[str, Any]] = Field(default_factory=list)
    risk_signals: list[dict[str, Any]] = Field(default_factory=list)
