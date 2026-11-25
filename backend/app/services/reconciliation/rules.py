from decimal import Decimal

from app.services.reconciliation.money import ZERO, compute_line_extension, quantize_money
from app.services.reconciliation.types import (
    InvoiceInput,
    InvoiceLineInput,
    LineQuantityBreakdown,
    POInput,
    POLineInput,
    RuleOutcome,
    RuleResultStatus,
    ToleranceRule,
)


def _allowed_delta(base: Decimal, abs_tol: Decimal, pct_tol: Decimal) -> Decimal:
    return max(abs_tol, abs(base) * pct_tol)


def evaluate_price_rule(
    po_line: POLineInput,
    inv_line: InvoiceLineInput,
    tol: ToleranceRule,
    currency: str,
) -> RuleOutcome:
    expected = quantize_money(po_line.unit_price, currency)
    actual = quantize_money(inv_line.unit_price, currency)
    variance = quantize_money(actual - expected, currency)
    abs_var = abs(variance)
    allowed = _allowed_delta(expected, tol.price_abs_tolerance, tol.price_pct_tolerance)

    tol_desc = f"abs<={tol.price_abs_tolerance}, pct<={tol.price_pct_tolerance * Decimal('100')}%"
    if abs_var == ZERO:
        res = RuleResultStatus.PASS
    elif abs_var <= allowed:
        res = RuleResultStatus.PASS_WITH_TOLERANCE
    else:
        res = RuleResultStatus.FAIL

    return RuleOutcome(
        rule_id="R-PRC-01",
        entity_line_id=inv_line.line_id,
        field_name="unit_price",
        expected_value=str(expected),
        actual_value=str(actual),
        variance=str(variance),
        tolerance_applied=tol_desc,
        result=res,
        breakdown={
            "po_line_id": po_line.line_id,
            "invoice_line_id": inv_line.line_id,
            "abs_variance": str(abs_var),
            "allowed_delta": str(quantize_money(allowed, currency)),
        },
    )


def evaluate_quantity_rules(
    qb: LineQuantityBreakdown,
    tol: ToleranceRule,
) -> list[RuleOutcome]:
    outcomes: list[RuleOutcome] = []

    if qb.uom_mismatches:
        outcomes.append(
            RuleOutcome(
                rule_id="R-UOM-01",
                entity_line_id=qb.po_line_id,
                field_name="uom",
                expected_value=qb.uom,
                actual_value="; ".join(qb.uom_mismatches),
                variance="MISMATCH",
                tolerance_applied="exact",
                result=RuleResultStatus.FAIL,
                breakdown={"po_line_id": qb.po_line_id, "mismatches": "; ".join(qb.uom_mismatches)},
            )
        )

    over = qb.potential_over_billing
    allowed_qty = _allowed_delta(
        qb.eligible_to_invoice, tol.qty_abs_tolerance, tol.qty_pct_tolerance
    )
    tol_desc = f"abs<={tol.qty_abs_tolerance}, pct<={tol.qty_pct_tolerance * Decimal('100')}%"

    if over > ZERO:
        res = RuleResultStatus.PASS_WITH_TOLERANCE if over <= allowed_qty else RuleResultStatus.FAIL
    else:
        res = RuleResultStatus.PASS

    outcomes.append(
        RuleOutcome(
            rule_id="R-QTY-01",
            entity_line_id=qb.po_line_id,
            field_name="invoiced_quantity",
            expected_value=str(qb.eligible_to_invoice),
            actual_value=str(qb.invoiced_qty),
            variance=str(over),
            tolerance_applied=tol_desc,
            result=res,
            breakdown={
                "ordered_qty": str(qb.ordered_qty),
                "received_qty": str(qb.received_qty),
                "accepted_qty": str(qb.accepted_qty),
                "rejected_qty": str(qb.rejected_qty),
                "invoiced_qty": str(qb.invoiced_qty),
                "eligible_qty": str(qb.eligible_to_invoice),
                "remaining_to_receive": str(qb.remaining_to_receive),
                "potential_over_billing": str(over),
            },
        )
    )

    if qb.potential_under_billing > ZERO:
        under_res = RuleResultStatus.INFO if tol.allow_partial_billing else RuleResultStatus.FAIL
        outcomes.append(
            RuleOutcome(
                rule_id="R-QTY-02",
                entity_line_id=qb.po_line_id,
                field_name="under_billed_quantity",
                expected_value=str(qb.eligible_to_invoice),
                actual_value=str(qb.invoiced_qty),
                variance=str(qb.potential_under_billing),
                tolerance_applied=(
                    "partial_billing_allowed" if tol.allow_partial_billing else "exact"
                ),
                result=under_res,
                breakdown={
                    "eligible_qty": str(qb.eligible_to_invoice),
                    "invoiced_qty": str(qb.invoiced_qty),
                    "potential_under_billing": str(qb.potential_under_billing),
                },
            )
        )

    return outcomes


def evaluate_invoice_header_rules(
    po: POInput,
    inv: InvoiceInput,
    tol: ToleranceRule,
) -> list[RuleOutcome]:
    outcomes: list[RuleOutcome] = []

    # R-SUP-01: Supplier mismatch
    sup_match = inv.vendor_id == po.vendor_id
    outcomes.append(
        RuleOutcome(
            rule_id="R-SUP-01",
            entity_line_id=inv.invoice_id,
            field_name="vendor_id",
            expected_value=po.vendor_id,
            actual_value=inv.vendor_id,
            variance="0" if sup_match else "MISMATCH",
            tolerance_applied="exact",
            result=RuleResultStatus.PASS if sup_match else RuleResultStatus.FAIL,
            breakdown={"po_vendor_id": po.vendor_id, "invoice_vendor_id": inv.vendor_id},
        )
    )

    # R-CUR-01: Currency mismatch
    cur_match = inv.currency.upper() == po.currency.upper()
    outcomes.append(
        RuleOutcome(
            rule_id="R-CUR-01",
            entity_line_id=inv.invoice_id,
            field_name="currency",
            expected_value=po.currency.upper(),
            actual_value=inv.currency.upper(),
            variance="0" if cur_match else "MISMATCH",
            tolerance_applied="exact",
            result=RuleResultStatus.PASS if cur_match else RuleResultStatus.FAIL,
            breakdown={
                "po_currency": po.currency.upper(),
                "invoice_currency": inv.currency.upper(),
            },
        )
    )

    # R-DUP-01: Exact duplicate invoice
    if inv.is_exact_duplicate:
        outcomes.append(
            RuleOutcome(
                rule_id="R-DUP-01",
                entity_line_id=inv.invoice_id,
                field_name="invoice_number",
                expected_value="unique",
                actual_value=inv.normalized_invoice_number,
                variance="DUPLICATE",
                tolerance_applied="unique_per_vendor_org",
                result=RuleResultStatus.FAIL,
                breakdown={
                    "invoice_id": inv.invoice_id,
                    "duplicate_of_invoice_id": inv.duplicate_of_invoice_id or "",
                    "normalized_invoice_number": inv.normalized_invoice_number,
                },
            )
        )

    # R-TOT-01: Invoice arithmetic totals consistency
    currency = inv.currency.upper()
    computed_sub = quantize_money(
        sum(
            (compute_line_extension(ln.quantity, ln.unit_price, currency) for ln in inv.lines),
            ZERO,
        ),
        currency,
    )
    computed_tax = quantize_money(sum((ln.tax_amount for ln in inv.lines), ZERO), currency)
    computed_disc = quantize_money(sum((ln.discount_amount for ln in inv.lines), ZERO), currency)
    computed_total = quantize_money(
        computed_sub - computed_disc + computed_tax + inv.freight_amount, currency
    )
    tot_var = quantize_money(inv.total_amount - computed_total, currency)
    outcomes.append(
        RuleOutcome(
            rule_id="R-TOT-01",
            entity_line_id=inv.invoice_id,
            field_name="total_amount",
            expected_value=str(computed_total),
            actual_value=str(quantize_money(inv.total_amount, currency)),
            variance=str(tot_var),
            tolerance_applied="exact",
            result=RuleResultStatus.PASS if abs(tot_var) == ZERO else RuleResultStatus.FAIL,
            breakdown={
                "computed_subtotal": str(computed_sub),
                "computed_discount": str(computed_disc),
                "computed_tax": str(computed_tax),
                "freight": str(quantize_money(inv.freight_amount, currency)),
                "computed_total": str(computed_total),
                "declared_total": str(quantize_money(inv.total_amount, currency)),
            },
        )
    )

    # R-TAX-01: Tax variance vs PO-line expected tax rates applied to invoiced line extensions
    po_lines_by_id = {pl.line_id: pl for pl in po.lines}
    expected_tax = ZERO
    for il in inv.lines:
        pl = po_lines_by_id.get(il.po_line_id or "")
        rate = pl.tax_rate if pl is not None else il.tax_rate
        ext = compute_line_extension(il.quantity, il.unit_price, currency)
        expected_tax += quantize_money(ext * rate, currency)
    expected_tax = quantize_money(expected_tax, currency)
    actual_tax = quantize_money(inv.tax_amount, currency)
    tax_var = quantize_money(actual_tax - expected_tax, currency)
    abs_tax_var = abs(tax_var)
    if abs_tax_var == ZERO:
        tax_res = RuleResultStatus.PASS
    elif abs_tax_var <= tol.tax_abs_tolerance:
        tax_res = RuleResultStatus.PASS_WITH_TOLERANCE
    else:
        tax_res = RuleResultStatus.FAIL

    outcomes.append(
        RuleOutcome(
            rule_id="R-TAX-01",
            entity_line_id=inv.invoice_id,
            field_name="tax_amount",
            expected_value=str(expected_tax),
            actual_value=str(actual_tax),
            variance=str(tax_var),
            tolerance_applied=f"abs<={tol.tax_abs_tolerance}",
            result=tax_res,
            breakdown={
                "expected_tax": str(expected_tax),
                "actual_tax": str(actual_tax),
                "tax_abs_tolerance": str(tol.tax_abs_tolerance),
            },
        )
    )

    return outcomes
