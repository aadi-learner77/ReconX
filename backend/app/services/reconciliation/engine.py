from decimal import Decimal

from app.services.reconciliation.money import ZERO, quantize_money
from app.services.reconciliation.quantities import aggregate_line_quantities
from app.services.reconciliation.rules import (
    evaluate_invoice_header_rules,
    evaluate_price_rule,
    evaluate_quantity_rules,
)
from app.services.reconciliation.types import (
    ExceptionDraft,
    LineQuantityBreakdown,
    MatchOutcome,
    POLineInput,
    ReconciliationInput,
    ReconciliationOutput,
    RuleOutcome,
    RuleResultStatus,
)

RULE_VERSION = "1.0.0"


def _exception_type_for_rule(rule_id: str) -> tuple[str, str]:
    mapping = {
        "R-PO-01": ("MISSING_PO", "HIGH"),
        "R-GRN-01": ("MISSING_GRN", "HIGH"),
        "R-SUP-01": ("SUPPLIER_MISMATCH", "HIGH"),
        "R-CUR-01": ("CURRENCY_MISMATCH", "HIGH"),
        "R-DUP-01": ("DUPLICATE_INVOICE", "HIGH"),
        "R-QTY-01": ("QTY_OVER_BILLED", "HIGH"),
        "R-QTY-02": ("QTY_UNDER_BILLED", "LOW"),
        "R-UOM-01": ("UOM_MISMATCH", "MEDIUM"),
        "R-PRC-01": ("PRICE_VARIANCE", "MEDIUM"),
        "R-TAX-01": ("TAX_VARIANCE", "MEDIUM"),
        "R-TOT-01": ("ARITHMETIC_MISMATCH", "HIGH"),
        "R-CONF-01": ("LOW_EXTRACTION_CONFIDENCE", "MEDIUM"),
        "R-LINK-01": ("AMBIGUOUS_LINK", "MEDIUM"),
    }
    return mapping.get(rule_id, ("RECONCILIATION_EXCEPTION", "MEDIUM"))


def reconcile_transaction(inp: ReconciliationInput) -> ReconciliationOutput:
    """Pure deterministic three-way matching engine (PO + GRNs + Invoices).

    Never imports DB, HTTP, or LLM modules and never uses binary float.
    """
    rule_results: list[RuleOutcome] = []
    exceptions: list[ExceptionDraft] = []
    line_breakdowns: list[LineQuantityBreakdown] = []

    po = inp.purchase_order
    currency = (
        po.currency
        if po is not None
        else (inp.invoices[0].currency if inp.invoices else "INR")
    ).upper()

    invoiced_total = quantize_money(
        sum((inv.total_amount for inv in inp.invoices), ZERO), currency
    )
    ordered_total = quantize_money(po.total_amount, currency) if po is not None else ZERO

    # Gate 1: Low extraction confidence or ambiguous links require human review first
    if inp.low_confidence_fields:
        rule = RuleOutcome(
            rule_id="R-CONF-01",
            entity_line_id=inp.transaction_id,
            field_name=", ".join(inp.low_confidence_fields),
            expected_value="verified_confidence",
            actual_value="low_confidence_unverified",
            variance="REVIEW",
            tolerance_applied="confidence_threshold",
            result=RuleResultStatus.REVIEW_REQUIRED,
            breakdown={"fields": ", ".join(inp.low_confidence_fields)},
        )
        rule_results.append(rule)
        exceptions.append(
            ExceptionDraft(
                exception_type="LOW_EXTRACTION_CONFIDENCE",
                severity="MEDIUM",
                rule_id="R-CONF-01",
                summary=(
                    "Human review required for low-confidence fields: "
                    f"{', '.join(inp.low_confidence_fields)}"
                ),
                affected_fields=inp.low_confidence_fields,
                values={"fields": ", ".join(inp.low_confidence_fields)},
                evidence_refs=({"type": "transaction", "id": inp.transaction_id},),
            )
        )

    if inp.ambiguous_links:
        rule = RuleOutcome(
            rule_id="R-LINK-01",
            entity_line_id=inp.transaction_id,
            field_name="po_link",
            expected_value="unambiguous_po",
            actual_value=", ".join(inp.ambiguous_links),
            variance="AMBIGUOUS",
            tolerance_applied="exact",
            result=RuleResultStatus.REVIEW_REQUIRED,
            breakdown={"candidates": ", ".join(inp.ambiguous_links)},
        )
        rule_results.append(rule)
        exceptions.append(
            ExceptionDraft(
                exception_type="AMBIGUOUS_LINK",
                severity="MEDIUM",
                rule_id="R-LINK-01",
                summary="Ambiguous PO/document link requires human confirmation.",
                affected_fields=("po_id",),
                values={"candidates": ", ".join(inp.ambiguous_links)},
                evidence_refs=({"type": "transaction", "id": inp.transaction_id},),
            )
        )

    # Gate 2: Missing PO -> INCOMPLETE (AT-06)
    if po is None:
        r_po = RuleOutcome(
            rule_id="R-PO-01",
            entity_line_id=inp.transaction_id,
            field_name="po_id",
            expected_value="linked_po",
            actual_value="MISSING",
            variance="MISSING",
            tolerance_applied="required",
            result=RuleResultStatus.INCOMPLETE,
            breakdown={"transaction_id": inp.transaction_id},
        )
        rule_results.append(r_po)
        exceptions.append(
            ExceptionDraft(
                exception_type="MISSING_PO",
                severity="HIGH",
                rule_id="R-PO-01",
                summary="Invoice has no linked Purchase Order.",
                affected_fields=("po_id",),
                values={"expected": "linked_po", "actual": "MISSING"},
                evidence_refs=tuple(
                    {"type": "invoice", "id": inv.invoice_id, "number": inv.invoice_number}
                    for inv in inp.invoices
                ),
            )
        )
        return ReconciliationOutput(
            transaction_id=inp.transaction_id,
            rule_version=RULE_VERSION,
            outcome=MatchOutcome.INCOMPLETE,
            line_quantities=(),
            rule_results=tuple(rule_results),
            exceptions=tuple(exceptions),
            ordered_total=ZERO,
            accepted_supported_total=ZERO,
            invoiced_total=invoiced_total,
            undisputed_amount=ZERO,
            disputed_amount=invoiced_total,
            currency=currency,
        )

    # Gate 3: Missing GRN -> INCOMPLETE (unless service/advance policy explicitly allows)
    if (
        not inp.has_grn_documents or not inp.grn_lines
    ) and not inp.default_tolerance.allow_service_advance_billing:
        r_grn = RuleOutcome(
            rule_id="R-GRN-01",
            entity_line_id=po.po_id,
            field_name="goods_receipt",
            expected_value="at_least_one_grn",
            actual_value="MISSING",
            variance="MISSING",
            tolerance_applied="required",
            result=RuleResultStatus.INCOMPLETE,
            breakdown={"po_id": po.po_id, "po_number": po.po_number},
        )
        rule_results.append(r_grn)
        exceptions.append(
            ExceptionDraft(
                exception_type="MISSING_GRN",
                severity="HIGH",
                rule_id="R-GRN-01",
                summary=f"No Goods Receipt Note (GRN) found for PO {po.po_number}.",
                affected_fields=("goods_receipts",),
                values={"expected": "at_least_one_grn", "actual": "MISSING"},
                evidence_refs=({"type": "purchase_order", "id": po.po_id, "number": po.po_number},),
            )
        )

    # Gate 4: Missing Invoice -> INCOMPLETE
    if not inp.invoices:
        r_inv = RuleOutcome(
            rule_id="R-INV-01",
            entity_line_id=po.po_id,
            field_name="invoice",
            expected_value="at_least_one_invoice",
            actual_value="MISSING",
            variance="MISSING",
            tolerance_applied="required",
            result=RuleResultStatus.INCOMPLETE,
            breakdown={"po_id": po.po_id},
        )
        rule_results.append(r_inv)
        exceptions.append(
            ExceptionDraft(
                exception_type="MISSING_INVOICE",
                severity="MEDIUM",
                rule_id="R-INV-01",
                summary=f"No supplier invoice linked to PO {po.po_number}.",
                affected_fields=("invoices",),
                values={"expected": "at_least_one_invoice", "actual": "MISSING"},
                evidence_refs=({"type": "purchase_order", "id": po.po_id, "number": po.po_number},),
            )
        )

    # Evaluate invoice header rules
    all_inv_lines: list = []
    for inv in inp.invoices:
        all_inv_lines.extend(inv.lines)
        rule_results.extend(evaluate_invoice_header_rules(po, inv, inp.default_tolerance))

    # Aggregate quantities per PO line across ALL linked GRNs and ALL linked invoices
    po_line_map = {pl.line_id: pl for pl in po.lines}
    accepted_supported_total = ZERO
    disputed_amount = ZERO

    for pl in po.lines:
        tol = inp.line_tolerances.get(pl.line_id, inp.default_tolerance)
        qb = aggregate_line_quantities(pl, inp.grn_lines, tuple(all_inv_lines), tol)
        line_breakdowns.append(qb)
        rule_results.extend(evaluate_quantity_rules(qb, tol))

        # Supported gross value for accepted quantity (unit price * (1 + tax_rate))
        supported_qty = min(qb.invoiced_qty, qb.eligible_to_invoice)
        line_supported = quantize_money(
            supported_qty * pl.unit_price * (Decimal("1") + pl.tax_rate),
            currency,
        )
        accepted_supported_total += line_supported

        if qb.potential_over_billing > ZERO:
            disputed_amount += quantize_money(
                qb.potential_over_billing * pl.unit_price * (Decimal("1") + pl.tax_rate),
                currency,
            )

    # Evaluate line-level unit price rules
    for il in all_inv_lines:
        matched_po_line: POLineInput | None = po_line_map.get(il.po_line_id or "")
        if matched_po_line is None and il.item_code:
            matched_po_line = next((p for p in po.lines if p.item_code == il.item_code), None)
        if matched_po_line is not None:
            tol = inp.line_tolerances.get(matched_po_line.line_id, inp.default_tolerance)
            prc_rule = evaluate_price_rule(matched_po_line, il, tol, currency)
            rule_results.append(prc_rule)
            if prc_rule.result == RuleResultStatus.FAIL:
                price_diff = (
                    abs(il.unit_price - matched_po_line.unit_price)
                    * il.quantity
                    * (Decimal("1") + matched_po_line.tax_rate)
                )
                disputed_amount += quantize_money(price_diff, currency)

    accepted_supported_total = quantize_money(accepted_supported_total, currency)
    disputed_amount = quantize_money(min(invoiced_total, disputed_amount), currency)
    undisputed_amount = quantize_money(max(ZERO, invoiced_total - disputed_amount), currency)

    # Create ExceptionDraft for every FAIL or INCOMPLETE rule not already emitted by gates
    existing_gate_rules = {e.rule_id for e in exceptions}
    for rr in rule_results:
        if (
            rr.result in (RuleResultStatus.FAIL, RuleResultStatus.INCOMPLETE)
            and rr.rule_id not in existing_gate_rules
        ):
            exc_type, sev = _exception_type_for_rule(rr.rule_id)
            exceptions.append(
                ExceptionDraft(
                    exception_type=exc_type,
                    severity=sev,
                    rule_id=rr.rule_id,
                    summary=(
                        f"{exc_type} on {rr.field_name}: expected {rr.expected_value}, "
                        f"actual {rr.actual_value} (variance {rr.variance})"
                    ),
                    affected_fields=(rr.field_name,),
                    values={
                        "expected": rr.expected_value,
                        "actual": rr.actual_value,
                        "variance": rr.variance,
                        "tolerance": rr.tolerance_applied,
                    },
                    evidence_refs=(
                        {
                            "type": "rule",
                            "rule_id": rr.rule_id,
                            "entity_line_id": rr.entity_line_id,
                        },
                    ),
                )
            )

    # Determine final outcome per SRS 6.5 priority order
    statuses = {r.result for r in rule_results}
    if RuleResultStatus.INCOMPLETE in statuses:
        final_outcome = MatchOutcome.INCOMPLETE
    elif RuleResultStatus.FAIL in statuses:
        final_outcome = MatchOutcome.EXCEPTION
    elif RuleResultStatus.REVIEW_REQUIRED in statuses:
        final_outcome = MatchOutcome.REVIEW_REQUIRED
    elif RuleResultStatus.PASS_WITH_TOLERANCE in statuses:
        final_outcome = MatchOutcome.MATCHED_WITH_TOLERANCE
    else:
        final_outcome = MatchOutcome.MATCHED

    # If duplicate invoice flagged, ensure outcome requires review/exception and undisputed = 0
    if any(inv.is_exact_duplicate for inv in inp.invoices):
        disputed_amount = invoiced_total
        undisputed_amount = ZERO

    return ReconciliationOutput(
        transaction_id=inp.transaction_id,
        rule_version=RULE_VERSION,
        outcome=final_outcome,
        line_quantities=tuple(line_breakdowns),
        rule_results=tuple(rule_results),
        exceptions=tuple(exceptions),
        ordered_total=ordered_total,
        accepted_supported_total=accepted_supported_total,
        invoiced_total=invoiced_total,
        undisputed_amount=undisputed_amount,
        disputed_amount=disputed_amount,
        currency=currency,
    )
