from typing import Any
from uuid import UUID

from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext
from app.models.domain import Document, ExceptionCase, GoodsReceipt, Invoice, PurchaseOrder
from app.repositories.base import OrgScopedRepository
from app.services.agents.tools import AgentToolbox
from app.services.llm.adapter import get_llm_provider, wrap_untrusted_text


class EvidenceRefItem(BaseModel):
    type: str  # purchase_order | goods_receipt | invoice | document | rule | exception_case
    id: str
    label: str = ""


class InvestigationOutputSchema(BaseModel):
    summary: str
    facts: list[str]
    discrepancies: list[str]
    evidence_refs: list[EvidenceRefItem]
    rule_ids: list[str]
    hypotheses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_indicators: list[str] = Field(default_factory=list)
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: str
    human_approval_required: bool = True
    ai_assisted: bool = True


KNOWN_RULE_IDS = {
    "R-PO-01",
    "R-GRN-01",
    "R-INV-01",
    "R-SUP-01",
    "R-CUR-01",
    "R-DUP-01",
    "R-QTY-01",
    "R-QTY-02",
    "R-UOM-01",
    "R-PRC-01",
    "R-TAX-01",
    "R-TOT-01",
    "R-CONF-01",
    "R-LINK-01",
}


def validate_evidence_refs(
    db: Session,
    organization_id: UUID,
    refs: list[EvidenceRefItem],
) -> list[EvidenceRefItem]:
    """Post-validator rejecting any fabricated/unresolvable evidence_ref (FR-EXC-06)."""
    for ref in refs:
        if ref.type == "rule":
            if ref.id not in KNOWN_RULE_IDS:
                raise AppError(
                    code="HALLUCINATED_EVIDENCE_REF",
                    message=f"Investigation referenced unknown rule_id '{ref.id}'.",
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )
            continue
        try:
            uid = UUID(ref.id)
        except ValueError as exc:
            raise AppError(
                code="HALLUCINATED_EVIDENCE_REF",
                message=f"Invalid UUID evidence_ref '{ref.id}'.",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            ) from exc

        model_map: dict[str, Any] = {
            "purchase_order": PurchaseOrder,
            "goods_receipt": GoodsReceipt,
            "invoice": Invoice,
            "document": Document,
            "exception_case": ExceptionCase,
        }
        model_cls = model_map.get(ref.type)
        if not model_cls:
            raise AppError(
                code="HALLUCINATED_EVIDENCE_REF",
                message=f"Unsupported evidence_ref type '{ref.type}'.",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        found = OrgScopedRepository(db, model_cls, organization_id).get_by_id(uid)
        if not found:
            raise AppError(
                code="HALLUCINATED_EVIDENCE_REF",
                message=f"Evidence reference {ref.type}:{ref.id} does not exist in organization.",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
    return refs


def run_case_investigation(
    db: Session,
    *,
    case_id: UUID,
    current_user: CurrentUserContext,
) -> dict[str, Any]:
    """Run bounded investigation over allowlisted read tools (SRS 7.2-7.5, UC-03, AT-08)."""
    case = OrgScopedRepository(db, ExceptionCase, current_user.organization_id).get_by_id(case_id)
    if not case:
        raise AppError("CASE_NOT_FOUND", "Exception case not found.", status.HTTP_404_NOT_FOUND)

    toolbox = AgentToolbox(db, current_user)
    bundle = toolbox.get_transaction_bundle(case.transaction_id)
    vendor_id_str = (bundle.get("vendor") or {}).get("id")
    vendor_history = (
        toolbox.get_vendor_history(UUID(vendor_id_str)) if vendor_id_str else {}
    )
    risks = toolbox.evaluate_risks(case.transaction_id)

    # Build grounded facts & real evidence references ONLY from retrieved DB records
    facts: list[str] = [
        f"Exception {case.type} ({case.severity}) opened under rule {case.rule_id}."
    ]
    discrepancies: list[str] = [case.summary]
    evidence_refs: list[EvidenceRefItem] = [
        EvidenceRefItem(type="exception_case", id=str(case.id), label=f"Case {case.type}"),
    ]
    if case.rule_id in KNOWN_RULE_IDS:
        evidence_refs.append(EvidenceRefItem(type="rule", id=case.rule_id, label=case.rule_id))

    po = bundle.get("purchase_order")
    if po:
        facts.append(
            f"PO {po['po_number']} ordered total {po['total_amount']} {po['currency']}."
        )
        evidence_refs.append(
            EvidenceRefItem(type="purchase_order", id=po["id"], label=po["po_number"])
        )
    grns = bundle.get("goods_receipts") or []
    for g in grns:
        acc = sum(float(ln["accepted_qty"]) for ln in g.get("lines", []))
        rej = sum(float(ln["rejected_qty"]) for ln in g.get("lines", []))
        facts.append(
            f"GRN {g['grn_number']} recorded accepted_qty={acc}, rejected_qty={rej}."
        )
        evidence_refs.append(
            EvidenceRefItem(type="goods_receipt", id=g["id"], label=g["grn_number"])
        )
    invs = bundle.get("invoices") or []
    for inv in invs:
        facts.append(
            f"Invoice {inv['invoice_number']} billed total {inv['total_amount']} {inv['currency']}."
        )
        evidence_refs.append(
            EvidenceRefItem(type="invoice", id=inv["id"], label=inv["invoice_number"])
        )

    missing_info: list[str] = []
    if not po:
        missing_info.append("No linked Purchase Order found for this transaction.")
    if not grns:
        missing_info.append("No Goods Receipt Note (GRN) recorded against this PO.")
    if not invs:
        missing_info.append("No Supplier Invoice linked to this PO.")

    hypotheses = [
        f"Hypothesis (unverified): {case.type} may reflect a partial shipment or supplier "
        "billing error; confirm with receiving/supplier before decision."
    ]
    risk_texts = [
        f"{r['signal_type']} ({r['severity']}, score={r['score']}): {r['label']}"
        for r in risks
    ]

    # Note: any document raw text passed to LLM is strictly wrapped as untrusted data
    llm = get_llm_provider()
    llm_payload = {
        "task": (
            "Summarize verified facts and discrepancies from tool outputs ONLY. "
            "Do not invent IDs or actions."
        ),
        "case": {
            "type": case.type,
            "rule_id": case.rule_id,
            "summary": wrap_untrusted_text(case.summary),
        },
        "facts": facts,
        "missing_information": missing_info,
        "vendor_tx_count": vendor_history.get("transaction_count", 0),
    }
    llm_out = llm.explain(llm_payload)

    recommended_action = (
        "Hold full payment approval; verify receipt/credit note or escalate to approver."
        if case.severity == "HIGH"
        else "Review variance against supporting documents and record decision rationale."
    )
    summary_text = (
        str(llm_out.get("summary"))
        if isinstance(llm_out, dict) and llm_out.get("summary")
        else (
            f"Investigation of {case.type} ({case.rule_id}): {case.summary} "
            f"Grounded across {len(grns)} GRN(s) and {len(invs)} invoice(s)."
        )
    )

    structured = InvestigationOutputSchema(
        summary=summary_text,
        facts=facts,
        discrepancies=discrepancies,
        evidence_refs=validate_evidence_refs(db, current_user.organization_id, evidence_refs),
        rule_ids=[case.rule_id] if case.rule_id else [],
        hypotheses=hypotheses,
        missing_information=missing_info,
        risk_indicators=risk_texts,
        recommended_action=recommended_action,
        confidence=0.90 if not missing_info else 0.72,
        limitations=(
            f"Vendor sample size N={vendor_history.get('transaction_count', 0)}; "
            "all automated findings require designated human review."
        ),
        human_approval_required=True,
        ai_assisted=True,
    )

    output_dict = structured.model_dump()
    output_dict["tool_trace"] = toolbox.tool_trace
    inv_row = toolbox.create_investigation_draft(
        case_id=case.id,
        structured_findings=output_dict,
        provider_name=llm.provider_name,
        model_name=llm.model_name,
        confidence=structured.confidence,
    )
    db.commit()

    return {
        "investigation_id": str(inv_row.id),
        "case_id": str(case.id),
        "status": inv_row.status,
        "model_provider": inv_row.model_provider,
        "model_name": inv_row.model_name,
        "prompt_version": inv_row.prompt_version,
        "confidence": float(inv_row.confidence),
        **output_dict,
    }
