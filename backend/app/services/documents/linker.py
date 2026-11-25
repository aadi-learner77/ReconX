from decimal import Decimal
from typing import Any
from uuid import UUID

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.models.domain import PurchaseOrder, Vendor
from app.repositories.base import OrgScopedRepository
from app.services.transactions.bundle import normalize_name


def find_po_link_candidates(
    db: Session,
    *,
    organization_id: UUID,
    po_reference: str | None,
    vendor_name: str | None,
    total_amount: Decimal | None,
    doc_date: Any = None,
) -> tuple[UUID | None, list[dict[str, Any]], bool]:
    """Match exact PO number first; controlled fallback returns CANDIDATE links only.

    Returns: (exact_po_id, candidate_list, is_ambiguous)
    """
    po_repo = OrgScopedRepository(db, PurchaseOrder, organization_id)
    if po_reference:
        exact_po = db.scalar(
            po_repo.base_query().where(PurchaseOrder.po_number == po_reference.strip())
        )
        if exact_po is not None:
            return (
                exact_po.id,
                [
                    {
                        "po_id": str(exact_po.id),
                        "po_number": exact_po.po_number,
                        "method": "exact_po_number",
                        "score": 1.0,
                    }
                ],
                False,
            )

    # Controlled fallback: vendor + amount tolerance window + optional date window
    candidates: list[dict[str, Any]] = []
    if not vendor_name:
        return None, [], False

    norm_v = normalize_name(vendor_name)
    vendors = list(
        db.scalars(OrgScopedRepository(db, Vendor, organization_id).base_query()).all()
    )
    matched_vendor_ids = [
        v.id
        for v in vendors
        if v.normalized_name == norm_v
        or fuzz.ratio(v.legal_name.lower(), vendor_name.lower()) >= 85
    ]
    if not matched_vendor_ids:
        return None, [], False

    pos = list(
        db.scalars(
            po_repo.base_query().where(PurchaseOrder.vendor_id.in_(matched_vendor_ids))
        ).all()
    )
    for po in pos:
        score = 0.5
        if total_amount is not None and po.total_amount > 0:
            diff_ratio = abs(po.total_amount - total_amount) / po.total_amount
            if diff_ratio <= Decimal("0.05"):
                score += 0.3
            else:
                continue
        if doc_date is not None:
            delta = abs((doc_date - po.issue_date).days)
            if delta <= 45:
                score += 0.2
            else:
                continue
        candidates.append(
            {
                "po_id": str(po.id),
                "po_number": po.po_number,
                "method": "controlled_fallback",
                "score": round(score, 2),
            }
        )

    # Fallback ALWAYS requires human review if >0 candidates; never auto-links
    is_ambiguous = len(candidates) > 0
    return None, candidates, is_ambiguous


def suggest_semantic_line_mappings(
    po_lines: list[dict[str, Any]],
    invoice_lines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use rapidfuzz similarity to suggest candidate line mappings (advisory only; FR-EXT-06)."""
    suggestions: list[dict[str, Any]] = []
    for idx, il in enumerate(invoice_lines):
        il_desc = str(il.get("description", ""))
        il_code = str(il.get("item_code", ""))
        best_po_line = None
        best_score = 0.0
        for pl in po_lines:
            if il_code and pl.get("item_code") == il_code:
                best_po_line = pl
                best_score = 100.0
                break
            sim = float(fuzz.token_sort_ratio(il_desc, str(pl.get("description", ""))))
            if sim > best_score:
                best_score = sim
                best_po_line = pl
        if best_po_line is not None and best_score >= 65.0:
            suggestions.append(
                {
                    "invoice_line_index": idx,
                    "suggested_po_line_id": str(best_po_line["id"]),
                    "similarity": round(best_score / 100.0, 2),
                    "advisory_only": True,
                }
            )
    return suggestions
