import ast
from decimal import Decimal
from pathlib import Path

from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from app.services.reconciliation import (
    GRNLineInput,
    InvoiceInput,
    InvoiceLineInput,
    MatchOutcome,
    POInput,
    POLineInput,
    ReconciliationInput,
    ToleranceRule,
    reconcile_transaction,
)
from app.services.reconciliation.money import quantize_money


def test_reconciliation_package_has_no_float_db_http_or_llm_imports() -> None:
    pkg_dir = Path(__file__).resolve().parents[1] / "app" / "services" / "reconciliation"
    forbidden_modules = {"sqlalchemy", "fastapi", "httpx", "requests", "openai", "anthropic"}
    for py_file in pkg_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in forbidden_modules, f"{py_file}: forbidden import {top}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden_modules, f"{py_file}: forbidden import {top}"
            elif isinstance(node, ast.Constant) and isinstance(node.value, float):
                raise AssertionError(f"{py_file}: float literal {node.value} is forbidden")
            elif isinstance(node, ast.Name) and node.id == "float":
                raise AssertionError(f"{py_file}: float usage is forbidden")


def _po_simple(qty: Decimal = Decimal("100"), price: Decimal = Decimal("100.00")) -> POInput:
    sub = quantize_money(qty * price, "INR")
    tax = quantize_money(sub * Decimal("0.18"), "INR")
    tot = quantize_money(sub + tax, "INR")
    return POInput(
        po_id="po-1",
        po_number="PO-1",
        vendor_id="v-1",
        currency="INR",
        subtotal_amount=sub,
        tax_amount=tax,
        discount_amount=Decimal("0"),
        freight_amount=Decimal("0"),
        total_amount=tot,
        lines=(
            POLineInput(
                line_id="pol-1",
                line_number=1,
                item_code="ITEM-1",
                description="Widget",
                uom="EA",
                quantity=qty,
                unit_price=price,
                tax_rate=Decimal("0.18"),
                tax_amount=tax,
                discount_amount=Decimal("0"),
                line_total=tot,
            ),
        ),
    )


def _inv_simple(
    *,
    inv_id: str = "inv-1",
    vendor_id: str = "v-1",
    qty: Decimal = Decimal("100"),
    price: Decimal = Decimal("100.00"),
    tax_override: Decimal | None = None,
    currency: str = "INR",
    uom: str = "EA",
    is_dup: bool = False,
) -> InvoiceInput:
    sub = quantize_money(qty * price, currency)
    tax = (
        quantize_money(tax_override, currency)
        if tax_override is not None
        else quantize_money(sub * Decimal("0.18"), currency)
    )
    tot = quantize_money(sub + tax, currency)
    return InvoiceInput(
        invoice_id=inv_id,
        invoice_number=f"INV-{inv_id}",
        normalized_invoice_number=f"INV{inv_id}".upper(),
        vendor_id=vendor_id,
        po_id="po-1",
        currency=currency,
        subtotal_amount=sub,
        tax_amount=tax,
        discount_amount=Decimal("0"),
        freight_amount=Decimal("0"),
        total_amount=tot,
        is_exact_duplicate=is_dup,
        lines=(
            InvoiceLineInput(
                line_id=f"il-{inv_id}",
                invoice_id=inv_id,
                po_line_id="pol-1",
                item_code="ITEM-1",
                description="Widget",
                uom=uom,
                quantity=qty,
                unit_price=price,
                tax_rate=Decimal("0.18"),
                tax_amount=tax,
                discount_amount=Decimal("0"),
                line_total=tot,
            ),
        ),
    )


def test_at01_exact_match() -> None:
    out = reconcile_transaction(
        ReconciliationInput(
            transaction_id="po-1",
            organization_id="org-1",
            purchase_order=_po_simple(),
            grn_lines=(
                GRNLineInput(
                    "g1",
                    "GRN-1",
                    "pol-1",
                    "ITEM-1",
                    "EA",
                    Decimal("100"),
                    Decimal("100"),
                    Decimal("0"),
                ),
            ),
            invoices=(_inv_simple(),),
            default_tolerance=ToleranceRule(),
        )
    )
    assert out.outcome == MatchOutcome.MATCHED
    assert out.exceptions == ()
    assert out.disputed_amount == Decimal("0.00")


def test_at02_partial_grn_over_billing_exception() -> None:
    out = reconcile_transaction(
        ReconciliationInput(
            transaction_id="po-1",
            organization_id="org-1",
            purchase_order=_po_simple(qty=Decimal("100")),
            grn_lines=(
                GRNLineInput(
                    "g1",
                    "GRN-1",
                    "pol-1",
                    "ITEM-1",
                    "EA",
                    Decimal("90"),
                    Decimal("90"),
                    Decimal("0"),
                ),
            ),
            invoices=(_inv_simple(qty=Decimal("100")),),
            default_tolerance=ToleranceRule(),
        )
    )
    assert out.outcome == MatchOutcome.EXCEPTION
    assert any(
        e.rule_id == "R-QTY-01" and e.exception_type == "QTY_OVER_BILLED" for e in out.exceptions
    )
    assert out.disputed_amount == Decimal("1180.00")
    assert out.undisputed_amount == Decimal("10620.00")


def test_at03_multiple_grns_aggregated_matched() -> None:
    out = reconcile_transaction(
        ReconciliationInput(
            transaction_id="po-1",
            organization_id="org-1",
            purchase_order=_po_simple(qty=Decimal("100")),
            grn_lines=(
                GRNLineInput(
                    "g1",
                    "GRN-1",
                    "pol-1",
                    "ITEM-1",
                    "EA",
                    Decimal("60"),
                    Decimal("60"),
                    Decimal("0"),
                ),
                GRNLineInput(
                    "g2",
                    "GRN-2",
                    "pol-1",
                    "ITEM-1",
                    "EA",
                    Decimal("40"),
                    Decimal("40"),
                    Decimal("0"),
                ),
            ),
            invoices=(_inv_simple(qty=Decimal("100")),),
            default_tolerance=ToleranceRule(),
        )
    )
    assert out.outcome == MatchOutcome.MATCHED
    assert out.line_quantities[0].accepted_qty == Decimal("100.0000")


def test_at04_price_tolerance_boundary_and_over() -> None:
    tol = ToleranceRule(price_abs_tolerance=Decimal("0"), price_pct_tolerance=Decimal("0.02"))
    grn = (
        GRNLineInput(
            "g1", "GRN-1", "pol-1", "ITEM-1", "EA", Decimal("100"), Decimal("100"), Decimal("0")
        ),
    )

    # Exactly at 2% tolerance -> MATCHED_WITH_TOLERANCE (never MATCHED)
    at_boundary = reconcile_transaction(
        ReconciliationInput(
            transaction_id="po-1",
            organization_id="org-1",
            purchase_order=_po_simple(price=Decimal("100.00")),
            grn_lines=grn,
            invoices=(_inv_simple(price=Decimal("102.00")),),
            default_tolerance=tol,
        )
    )
    assert at_boundary.outcome == MatchOutcome.MATCHED_WITH_TOLERANCE

    # Just over 2% tolerance -> EXCEPTION
    just_over = reconcile_transaction(
        ReconciliationInput(
            transaction_id="po-1",
            organization_id="org-1",
            purchase_order=_po_simple(price=Decimal("100.00")),
            grn_lines=grn,
            invoices=(_inv_simple(price=Decimal("102.01")),),
            default_tolerance=tol,
        )
    )
    assert just_over.outcome == MatchOutcome.EXCEPTION
    assert any(e.rule_id == "R-PRC-01" for e in just_over.exceptions)


def test_at05_duplicate_and_at06_missing_po() -> None:
    dup_out = reconcile_transaction(
        ReconciliationInput(
            transaction_id="po-1",
            organization_id="org-1",
            purchase_order=_po_simple(),
            grn_lines=(
                GRNLineInput(
                    "g1",
                    "GRN-1",
                    "pol-1",
                    "ITEM-1",
                    "EA",
                    Decimal("100"),
                    Decimal("100"),
                    Decimal("0"),
                ),
            ),
            invoices=(_inv_simple(is_dup=True),),
            default_tolerance=ToleranceRule(),
        )
    )
    assert dup_out.outcome == MatchOutcome.EXCEPTION
    assert any(e.rule_id == "R-DUP-01" for e in dup_out.exceptions)
    assert dup_out.undisputed_amount == Decimal("0.00")

    no_po_out = reconcile_transaction(
        ReconciliationInput(
            transaction_id="inv-1",
            organization_id="org-1",
            purchase_order=None,
            grn_lines=(),
            invoices=(_inv_simple(),),
            default_tolerance=ToleranceRule(),
        )
    )
    assert no_po_out.outcome == MatchOutcome.INCOMPLETE
    assert any(e.rule_id == "R-PO-01" for e in no_po_out.exceptions)


def test_supplier_tax_rejected_split_uom_currency_and_low_conf() -> None:
    grn = (
        GRNLineInput(
            "g1", "GRN-1", "pol-1", "ITEM-1", "EA", Decimal("100"), Decimal("100"), Decimal("0")
        ),
    )

    # Supplier mismatch
    sup_out = reconcile_transaction(
        ReconciliationInput(
            "po-1", "org-1", _po_simple(), grn, (_inv_simple(vendor_id="v-99"),), ToleranceRule()
        )
    )
    assert any(e.rule_id == "R-SUP-01" for e in sup_out.exceptions)

    # Tax variance
    tax_out = reconcile_transaction(
        ReconciliationInput(
            "po-1",
            "org-1",
            _po_simple(),
            grn,
            (_inv_simple(tax_override=Decimal("2400.00")),),
            ToleranceRule(),
        )
    )
    assert any(e.rule_id == "R-TAX-01" for e in tax_out.exceptions)

    # Rejected quantity: received 100, accepted 80, rejected 20; invoice 100 -> over-billed 20
    rej_out = reconcile_transaction(
        ReconciliationInput(
            "po-1",
            "org-1",
            _po_simple(qty=Decimal("100")),
            (
                GRNLineInput(
                    "g1",
                    "GRN-1",
                    "pol-1",
                    "ITEM-1",
                    "EA",
                    Decimal("100"),
                    Decimal("80"),
                    Decimal("20"),
                ),
            ),
            (_inv_simple(qty=Decimal("100")),),
            ToleranceRule(),
        )
    )
    assert rej_out.outcome == MatchOutcome.EXCEPTION
    assert rej_out.line_quantities[0].rejected_qty == Decimal("20.0000")
    assert rej_out.line_quantities[0].potential_over_billing == Decimal("20.0000")

    # Split invoice (60 + 40 = 100)
    split_out = reconcile_transaction(
        ReconciliationInput(
            "po-1",
            "org-1",
            _po_simple(qty=Decimal("100")),
            grn,
            (
                _inv_simple(inv_id="a", qty=Decimal("60")),
                _inv_simple(inv_id="b", qty=Decimal("40")),
            ),
            ToleranceRule(),
        )
    )
    assert split_out.outcome == MatchOutcome.MATCHED

    # UoM mismatch
    uom_out = reconcile_transaction(
        ReconciliationInput(
            "po-1", "org-1", _po_simple(), grn, (_inv_simple(uom="KG"),), ToleranceRule()
        )
    )
    assert any(e.rule_id == "R-UOM-01" for e in uom_out.exceptions)

    # Currency mismatch
    cur_out = reconcile_transaction(
        ReconciliationInput(
            "po-1", "org-1", _po_simple(), grn, (_inv_simple(currency="USD"),), ToleranceRule()
        )
    )
    assert any(e.rule_id == "R-CUR-01" for e in cur_out.exceptions)

    # Low confidence gate
    conf_out = reconcile_transaction(
        ReconciliationInput(
            "po-1",
            "org-1",
            _po_simple(),
            grn,
            (_inv_simple(),),
            ToleranceRule(),
            low_confidence_fields=("total_amount",),
        )
    )
    assert conf_out.outcome == MatchOutcome.REVIEW_REQUIRED


@hyp_settings(max_examples=40)
@given(
    q1=st.integers(min_value=1, max_value=500),
    q2=st.integers(min_value=1, max_value=500),
    price=st.decimals(min_value=Decimal("1.00"), max_value=Decimal("10000.00"), places=2),
)
def test_property_grn_order_invariance_and_decimal_stability(
    q1: int, q2: int, price: Decimal
) -> None:
    d1, d2 = Decimal(q1), Decimal(q2)
    po = _po_simple(qty=d1 + d2, price=price)
    g1 = GRNLineInput("g1", "GRN-1", "pol-1", "ITEM-1", "EA", d1, d1, Decimal("0"))
    g2 = GRNLineInput("g2", "GRN-2", "pol-1", "ITEM-1", "EA", d2, d2, Decimal("0"))
    inv = _inv_simple(qty=d1 + d2, price=price)

    out_ab = reconcile_transaction(
        ReconciliationInput("po-1", "org-1", po, (g1, g2), (inv,), ToleranceRule())
    )
    out_ba = reconcile_transaction(
        ReconciliationInput("po-1", "org-1", po, (g2, g1), (inv,), ToleranceRule())
    )
    assert out_ab.outcome == out_ba.outcome == MatchOutcome.MATCHED
    assert out_ab.accepted_supported_total == out_ba.accepted_supported_total
    assert isinstance(out_ab.invoiced_total, Decimal)
    assert out_ab.invoiced_total == quantize_money(out_ab.invoiced_total, "INR")
