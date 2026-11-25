from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class MatchOutcome(StrEnum):
    MATCHED = "MATCHED"
    MATCHED_WITH_TOLERANCE = "MATCHED_WITH_TOLERANCE"
    EXCEPTION = "EXCEPTION"
    INCOMPLETE = "INCOMPLETE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class RuleResultStatus(StrEnum):
    PASS = "PASS"
    PASS_WITH_TOLERANCE = "PASS_WITH_TOLERANCE"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INFO = "INFO"


@dataclass(frozen=True)
class POLineInput:
    line_id: str
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


@dataclass(frozen=True)
class POInput:
    po_id: str
    po_number: str
    vendor_id: str
    currency: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    freight_amount: Decimal
    total_amount: Decimal
    lines: tuple[POLineInput, ...]


@dataclass(frozen=True)
class GRNLineInput:
    grn_id: str
    grn_number: str
    po_line_id: str | None
    item_code: str
    uom: str
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal


@dataclass(frozen=True)
class InvoiceLineInput:
    line_id: str
    invoice_id: str
    po_line_id: str | None
    item_code: str
    description: str
    uom: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class InvoiceInput:
    invoice_id: str
    invoice_number: str
    normalized_invoice_number: str
    vendor_id: str
    po_id: str | None
    currency: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    freight_amount: Decimal
    total_amount: Decimal
    is_exact_duplicate: bool = False
    duplicate_of_invoice_id: str | None = None
    lines: tuple[InvoiceLineInput, ...] = ()


@dataclass(frozen=True)
class ToleranceRule:
    price_abs_tolerance: Decimal = Decimal("0")
    price_pct_tolerance: Decimal = Decimal("0.02")
    qty_abs_tolerance: Decimal = Decimal("0")
    qty_pct_tolerance: Decimal = Decimal("0")
    tax_abs_tolerance: Decimal = Decimal("1.00")
    allow_partial_billing: bool = True
    allow_service_advance_billing: bool = False


@dataclass(frozen=True)
class ReconciliationInput:
    transaction_id: str
    organization_id: str
    purchase_order: POInput | None
    grn_lines: tuple[GRNLineInput, ...]
    invoices: tuple[InvoiceInput, ...]
    default_tolerance: ToleranceRule
    line_tolerances: dict[str, ToleranceRule] = field(default_factory=dict)
    low_confidence_fields: tuple[str, ...] = ()
    ambiguous_links: tuple[str, ...] = ()
    has_grn_documents: bool = True


@dataclass(frozen=True)
class LineQuantityBreakdown:
    po_line_id: str
    item_code: str
    uom: str
    ordered_qty: Decimal
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    invoiced_qty: Decimal
    remaining_to_receive: Decimal
    eligible_to_invoice: Decimal
    potential_over_billing: Decimal
    potential_under_billing: Decimal
    uom_mismatches: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    entity_line_id: str
    field_name: str
    expected_value: str
    actual_value: str
    variance: str
    tolerance_applied: str
    result: RuleResultStatus
    breakdown: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExceptionDraft:
    exception_type: str
    severity: str
    rule_id: str
    summary: str
    affected_fields: tuple[str, ...]
    values: dict[str, str]
    evidence_refs: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class ReconciliationOutput:
    transaction_id: str
    rule_version: str
    outcome: MatchOutcome
    line_quantities: tuple[LineQuantityBreakdown, ...]
    rule_results: tuple[RuleOutcome, ...]
    exceptions: tuple[ExceptionDraft, ...]
    ordered_total: Decimal
    accepted_supported_total: Decimal
    invoiced_total: Decimal
    undisputed_amount: Decimal
    disputed_amount: Decimal
    currency: str
