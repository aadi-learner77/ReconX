import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field

from app.services.documents.ocr import OCRTextBlock
from app.services.llm.adapter import LLMProvider, get_llm_provider


class ExtractedLineSchema(BaseModel):
    item_code: str = ""
    description: str
    uom: str = "EA"
    quantity: str
    unit_price: str = "0.00"
    tax_amount: str = "0.00"
    line_total: str = "0.00"


class ExtractedDocSchema(BaseModel):
    document_number: str | None = None
    po_reference: str | None = None
    vendor_name: str | None = None
    document_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal_amount: str | None = None
    tax_amount: str | None = None
    total_amount: str | None = None
    lines: list[ExtractedLineSchema] = Field(default_factory=list)


@dataclass(frozen=True)
class ExtractedFieldCandidate:
    field_name: str
    value: Any
    confidence: Decimal
    page: int
    bbox: dict[str, float] | None
    evidence_ref: str
    extraction_method: str


def classify_document(
    text: str, hint: str | None = None, llm: LLMProvider | None = None
) -> tuple[str, Decimal]:
    upper = text.upper()
    scores = {
        "INVOICE": sum(
            1
            for kw in ["TAX INVOICE", "INVOICE NO", "INVOICE NUMBER", "AMOUNT DUE", "BILL TO"]
            if kw in upper
        ),
        "GRN": sum(
            1
            for kw in ["GOODS RECEIPT", "GRN", "ACCEPTED QTY", "RECEIVED QTY", "REJECTED QTY"]
            if kw in upper
        ),
        "PO": sum(
            1
            for kw in ["PURCHASE ORDER", "PO NUMBER", "PO NO", "SHIP TO", "ORDERED QTY"]
            if kw in upper
        ),
    }
    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    if best_score >= 2:
        return best_type, Decimal("0.9400")
    if best_score == 1:
        return best_type, Decimal("0.8200")
    if hint and hint.upper() in {"PO", "GRN", "INVOICE"}:
        return hint.upper(), Decimal("0.7500")

    provider = llm or get_llm_provider()
    llm_res = provider.classify(text)
    dtype = llm_res.document_type.upper()
    if dtype not in {"PO", "GRN", "INVOICE", "UNKNOWN"}:
        dtype = "UNKNOWN"
    conf = Decimal(str(round(max(0.0, min(1.0, llm_res.confidence)), 4)))
    return dtype, conf


def _find_block_for_match(
    blocks: list[OCRTextBlock], pattern: str
) -> tuple[str | None, OCRTextBlock | None]:
    regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for blk in blocks:
        m = regex.search(blk.text)
        if m:
            return m.group(1).strip(), blk
    full = "\n".join(b.text for b in blocks)
    m = regex.search(full)
    if m:
        return m.group(1).strip(), blocks[0] if blocks else None
    return None, None


def _parse_decimal_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = re.sub(r"[,\s₹$€£]", "", raw.strip())
    try:
        val = Decimal(cleaned)
        return str(val)
    except InvalidOperation:
        return None


def _parse_lines_from_blocks(blocks: list[OCRTextBlock]) -> list[dict[str, str]]:
    full_text = "\n".join(b.text for b in blocks)
    lines: list[dict[str, str]] = []
    # Match structured rows: ITEM_CODE | Description | UOM | Qty | UnitPrice | Tax | LineTotal
    # or whitespace/pipe-separated rows
    row_regex = re.compile(
        r"([A-Z0-9\-]{3,20})\s*[|\t ]+\s*([A-Za-z0-9\-\s/\.]{3,60}?)\s*[|\t ]+\s*"
        r"(EA|KG|MTR|ROLL|DRUM|BOX|NOS|PCS)\s*[|\t ]+\s*"
        r"([\d,]+(?:\.\d+)?)\s*[|\t ]+\s*([\d,]+(?:\.\d+)?)"
        r"(?:\s*[|\t ]+\s*([\d,]+(?:\.\d+)?))?"
        r"(?:\s*[|\t ]+\s*([\d,]+(?:\.\d+)?))?",
        re.IGNORECASE,
    )
    for m in row_regex.finditer(full_text):
        qty = _parse_decimal_str(m.group(4)) or "0"
        price = _parse_decimal_str(m.group(5)) or "0"
        tax = _parse_decimal_str(m.group(6)) or "0"
        total = _parse_decimal_str(m.group(7))
        if total is None:
            total = str(Decimal(qty) * Decimal(price) + Decimal(tax))
        lines.append(
            {
                "item_code": m.group(1).strip(),
                "description": m.group(2).strip(),
                "uom": m.group(3).upper(),
                "quantity": qty,
                "unit_price": price,
                "tax_amount": tax,
                "line_total": total,
            }
        )
    return lines


def extract_fields_from_blocks(
    blocks: list[OCRTextBlock],
    doc_type: str,
    llm: LLMProvider | None = None,
) -> tuple[list[ExtractedFieldCandidate], list[str]]:
    """Extract fields with provenance, run validation, and return validation warnings."""
    full_text = "\n".join(b.text for b in blocks)
    avg_ocr_conf = (
        sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0
    )

    candidates: list[ExtractedFieldCandidate] = []
    patterns: dict[str, str] = {
        "document_number": (
            r"(?:\bInvoice\s*(?:No|Number|#)|\bPO\s*(?:No|Number|#)"
            r"|\bGRN\s*(?:No|Number|#))[:\s#]+([A-Z0-9\-/]+)"
        ),
        "po_reference": (
            r"(?:\bPO\s*(?:Ref|Reference|Number|No)|\bPurchase\s*Order)"
            r"[:\s#]+([A-Z0-9\-/]+)"
        ),
        "vendor_name": r"(?:\bSupplier|\bVendor|\bFrom)[:\s]+([A-Za-z0-9\s&\.\-]+?)(?:\n|$|\|)",
        "document_date": (
            r"(?:\bInvoice\s*Date|\bIssue\s*Date|\bReceived\s*Date|\bDate)"
            r"[:\s]+(\d{4}-\d{2}-\d{2})"
        ),
        "due_date": r"(?:\bDue\s*Date)[:\s]+(\d{4}-\d{2}-\d{2})",
        "currency": r"(?:\bCurrency)[:\s]+(INR|USD|EUR|GBP|JPY)",
        "subtotal_amount": r"(?:\bSubtotal)[:\s₹$€£]*([\d,]+(?:\.\d{1,4})?)",
        "tax_amount": (
            r"(?:\bTax\s*Amount|\bGST|\bVAT|\bTax)[:\s₹$€£]*([\d,]+(?:\.\d{1,4})?)"
        ),
        "total_amount": (
            r"(?:\bGrand\s*Total|\bTotal\s*Amount|\bTotal)[:\s₹$€£]*([\d,]+(?:\.\d{1,4})?)"
        ),
    }
    if doc_type == "PO":
        patterns["document_number"] = r"(?:\bPO\s*(?:No|Number|#))[:\s#]+([A-Z0-9\-/]+)"
    elif doc_type == "GRN":
        patterns["document_number"] = r"(?:\bGRN\s*(?:No|Number|#))[:\s#]+([A-Z0-9\-/]+)"

    extracted_map: dict[str, str] = {}
    for fname, pat in patterns.items():
        val, blk = _find_block_for_match(blocks, pat)
        if val is not None and blk is not None:
            if fname in {"subtotal_amount", "tax_amount", "total_amount"}:
                num_str = _parse_decimal_str(val)
                if num_str is None:
                    continue
                val = num_str
            extracted_map[fname] = val
            conf = Decimal(str(round(min(0.98, blk.confidence), 4)))
            candidates.append(
                ExtractedFieldCandidate(
                    field_name=fname,
                    value=val,
                    confidence=conf,
                    page=blk.page,
                    bbox=blk.bbox,
                    evidence_ref=f"page:{blk.page}:{blk.method}",
                    extraction_method=f"regex+{blk.method}",
                )
            )

    # Check if explicit low-confidence marker is embedded in text (e.g. blurred/noisy scan flag)
    if avg_ocr_conf < 0.78 or "BLURRED" in full_text.upper() or "ILLEGIBLE" in full_text.upper():
        adjusted: list[ExtractedFieldCandidate] = []
        for c in candidates:
            if c.field_name == "total_amount":
                adjusted.append(
                    ExtractedFieldCandidate(
                        field_name=c.field_name,
                        value=c.value,
                        confidence=min(c.confidence, Decimal("0.5500")),
                        page=c.page,
                        bbox=c.bbox,
                        evidence_ref=c.evidence_ref,
                        extraction_method=c.extraction_method,
                    )
                )
            else:
                adjusted.append(c)
        candidates = adjusted

    line_items = _parse_lines_from_blocks(blocks)
    # Optional LLM fallback if regex missed key fields and provider is non-mock
    if len(extracted_map) < 3 and full_text.strip():
        provider = llm or get_llm_provider()
        llm_doc = provider.extract(full_text, ExtractedDocSchema)
        if isinstance(llm_doc, ExtractedDocSchema):
            for fname in [
                "document_number",
                "po_reference",
                "vendor_name",
                "document_date",
                "due_date",
                "currency",
                "subtotal_amount",
                "tax_amount",
                "total_amount",
            ]:
                if fname not in extracted_map:
                    v = getattr(llm_doc, fname)
                    if v:
                        extracted_map[fname] = str(v)
                        candidates.append(
                            ExtractedFieldCandidate(
                                field_name=fname,
                                value=str(v),
                                confidence=Decimal("0.7200"),
                                page=1,
                                bbox=None,
                                evidence_ref="page:1:llm",
                                extraction_method=f"llm:{provider.provider_name}",
                            )
                        )
            if not line_items and llm_doc.lines:
                line_items = [ln.model_dump() for ln in llm_doc.lines]

    if line_items:
        candidates.append(
            ExtractedFieldCandidate(
                field_name="line_items",
                value=line_items,
                confidence=Decimal(str(round(min(0.95, max(0.65, avg_ocr_conf)), 4))),
                page=1,
                bbox=blocks[0].bbox if blocks else None,
                evidence_ref="page:1:lines",
                extraction_method="regex+table",
            )
        )

    # Validation checks (FR-EXT-03)
    warnings = validate_extracted_fields(candidates, doc_type)
    return candidates, warnings


def validate_extracted_fields(
    candidates: list[ExtractedFieldCandidate], doc_type: str
) -> list[str]:
    by_name = {c.field_name: c.value for c in candidates}
    warnings: list[str] = []

    required = ["document_number", "vendor_name"]
    if doc_type == "INVOICE":
        required.extend(["total_amount", "currency"])
    for req in required:
        if not by_name.get(req):
            warnings.append(f"MISSING_REQUIRED:{req}")

    for df in ("document_date", "due_date"):
        if df in by_name and by_name[df]:
            try:
                date.fromisoformat(str(by_name[df]))
            except ValueError:
                warnings.append(f"INVALID_DATE:{df}")

    if "subtotal_amount" in by_name and "tax_amount" in by_name and "total_amount" in by_name:
        try:
            sub = Decimal(str(by_name["subtotal_amount"]))
            tax = Decimal(str(by_name["tax_amount"]))
            tot = Decimal(str(by_name["total_amount"]))
            if abs((sub + tax) - tot) > Decimal("1.00"):
                warnings.append("ARITHMETIC_TOTAL_MISMATCH")
        except InvalidOperation:
            warnings.append("INVALID_MONETARY_FORMAT")

    return warnings
