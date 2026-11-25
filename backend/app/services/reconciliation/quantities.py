
from app.services.reconciliation.money import ZERO, quantize_qty
from app.services.reconciliation.types import (
    GRNLineInput,
    InvoiceLineInput,
    LineQuantityBreakdown,
    POLineInput,
    ToleranceRule,
)


def aggregate_line_quantities(
    po_line: POLineInput,
    grn_lines: tuple[GRNLineInput, ...],
    invoice_lines: tuple[InvoiceLineInput, ...],
    tolerance: ToleranceRule,
) -> LineQuantityBreakdown:
    """Aggregate GRN and invoice quantities for one PO line without double-counting."""
    matched_grns = [
        g
        for g in grn_lines
        if (g.po_line_id == po_line.line_id)
        or (g.po_line_id is None and g.item_code and g.item_code == po_line.item_code)
    ]
    matched_invs = [
        il
        for il in invoice_lines
        if (il.po_line_id == po_line.line_id)
        or (il.po_line_id is None and il.item_code and il.item_code == po_line.item_code)
    ]

    received = ZERO
    accepted = ZERO
    rejected = ZERO
    uom_mismatches: list[str] = []

    for g in matched_grns:
        if g.uom.upper() != po_line.uom.upper():
            uom_mismatches.append(f"GRN {g.grn_number}: {g.uom} != {po_line.uom}")
            continue
        received += g.received_qty
        accepted += g.accepted_qty
        rejected += g.rejected_qty

    invoiced = ZERO
    for il in matched_invs:
        if il.uom.upper() != po_line.uom.upper():
            uom_mismatches.append(f"Invoice line {il.line_id}: {il.uom} != {po_line.uom}")
            continue
        invoiced += il.quantity

    ordered = quantize_qty(po_line.quantity)
    received = quantize_qty(received)
    accepted = quantize_qty(accepted)
    rejected = quantize_qty(rejected)
    invoiced = quantize_qty(invoiced)

    remaining_to_receive = quantize_qty(max(ZERO, ordered - accepted - rejected))
    eligible_to_invoice = (
        ordered if tolerance.allow_service_advance_billing and accepted == ZERO else accepted
    )
    potential_over_billing = quantize_qty(max(ZERO, invoiced - eligible_to_invoice))
    potential_under_billing = quantize_qty(max(ZERO, eligible_to_invoice - invoiced))

    return LineQuantityBreakdown(
        po_line_id=po_line.line_id,
        item_code=po_line.item_code,
        uom=po_line.uom,
        ordered_qty=ordered,
        received_qty=received,
        accepted_qty=accepted,
        rejected_qty=rejected,
        invoiced_qty=invoiced,
        remaining_to_receive=remaining_to_receive,
        eligible_to_invoice=eligible_to_invoice,
        potential_over_billing=potential_over_billing,
        potential_under_billing=potential_under_billing,
        uom_mismatches=tuple(uom_mismatches),
    )
