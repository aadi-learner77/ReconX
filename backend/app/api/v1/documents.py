from datetime import UTC, date, datetime
from decimal import Decimal
from math import ceil
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import CurrentUserContext, require_permission
from app.models.domain import (
    Document,
    ExceptionCase,
    ExtractionField,
    GoodsReceipt,
    GRNLine,
    Invoice,
    InvoiceLine,
    Job,
    POLine,
    PurchaseOrder,
    RiskSignal,
    Vendor,
)
from app.repositories.base import OrgScopedRepository
from app.schemas.common import PaginatedResponse, paginate_params
from app.services.audit.service import record_audit_event
from app.services.documents.linker import find_po_link_candidates, suggest_semantic_line_mappings
from app.services.documents.storage import StorageAdapter
from app.services.documents.validation import validate_uploaded_file
from app.services.transactions.bundle import normalize_invoice_number, normalize_name
from app.workers.job_worker import enqueue_document_job

router = APIRouter(tags=["documents"])


class FieldCorrectionItem(BaseModel):
    field_name: str
    value: Any


class PatchFieldsRequest(BaseModel):
    corrections: list[FieldCorrectionItem] = Field(min_length=1)


class LinkDocumentRequest(BaseModel):
    po_id: UUID


def _doc_summary(doc: Document) -> dict[str, Any]:
    active_fields = [f for f in doc.fields if f.is_active]
    return {
        "document_id": str(doc.id),
        "organization_id": str(doc.organization_id),
        "file_name": doc.file_name,
        "mime_type": doc.mime_type,
        "file_size_bytes": doc.file_size_bytes,
        "checksum": doc.checksum,
        "classification": doc.document_type,
        "classification_confidence": float(doc.classification_confidence),
        "status": doc.status,
        "is_duplicate_file": doc.is_duplicate_file,
        "duplicate_of_document_id": (
            str(doc.duplicate_of_document_id) if doc.duplicate_of_document_id else None
        ),
        "transaction_id": str(doc.transaction_id) if doc.transaction_id else None,
        "created_at": doc.created_at.isoformat(),
        "fields": [
            {
                "id": str(f.id),
                "name": f.field_name,
                "value": f.value_json.get("value"),
                "confidence": float(f.confidence),
                "page": f.page,
                "bbox": f.bbox_json,
                "evidence_ref": f.evidence_ref,
                "extraction_method": f.extraction_method,
                "verification_status": f.verification_status,
                "verified": f.verification_status in {"user_corrected", "system_derived"}
                or float(f.confidence) >= 0.8,
                "version": f.version,
            }
            for f in sorted(active_fields, key=lambda x: x.field_name)
        ],
    }


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    document_type_hint: str | None = Form(default=None),
    transaction_id: UUID | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: CurrentUserContext = Depends(require_permission("documents:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    content = await file.read()
    ext, detected_mime = validate_uploaded_file(file.filename or "", content)

    doc_repo = OrgScopedRepository(db, Document, current_user.organization_id)
    if idempotency_key:
        existing_idem = db.scalar(
            doc_repo.base_query().where(Document.idempotency_key == idempotency_key)
        )
        if existing_idem:
            job = db.scalar(
                OrgScopedRepository(db, Job, current_user.organization_id)
                .base_query()
                .where(Job.entity_id == str(existing_idem.id))
                .order_by(desc(Job.created_at))
            )
            return {
                "document_id": str(existing_idem.id),
                "status": existing_idem.status,
                "job_id": str(job.id) if job else "",
                "is_duplicate_file": existing_idem.is_duplicate_file,
            }

    storage = StorageAdapter()
    storage_key, checksum = storage.save_bytes(content, ext)

    existing_checksum_doc = db.scalar(
        doc_repo.base_query()
        .where(Document.checksum == checksum)
        .order_by(asc(Document.created_at))
    )

    doc = Document(
        organization_id=current_user.organization_id,
        file_name=file.filename or f"upload.{ext}",
        storage_key=storage_key,
        checksum=checksum,
        mime_type=detected_mime,
        file_size_bytes=len(content),
        uploaded_by=current_user.id,
        document_type=(document_type_hint.upper() if document_type_hint else "UNKNOWN"),
        classification_confidence=Decimal("0.0000"),
        status="QUEUED",
        transaction_id=transaction_id,
        idempotency_key=idempotency_key,
        is_duplicate_file=existing_checksum_doc is not None,
        duplicate_of_document_id=existing_checksum_doc.id if existing_checksum_doc else None,
    )
    db.add(doc)
    db.flush()

    job_idem = idempotency_key or f"doc-{doc.id}"
    job = enqueue_document_job(
        db,
        organization_id=current_user.organization_id,
        document_id=doc.id,
        idempotency_key=job_idem,
        payload={"document_type_hint": document_type_hint},
    )

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="DOCUMENT_UPLOADED",
        entity_type="document",
        entity_id=str(doc.id),
        after={
            "file_name": doc.file_name,
            "checksum": checksum,
            "mime_type": detected_mime,
            "is_duplicate_file": doc.is_duplicate_file,
        },
    )
    db.commit()

    return {
        "document_id": str(doc.id),
        "status": doc.status,
        "job_id": str(job.id),
        "is_duplicate_file": doc.is_duplicate_file,
        "duplicate_of_document_id": (
            str(doc.duplicate_of_document_id) if doc.duplicate_of_document_id else None
        ),
    }


@router.get("/documents", response_model=PaginatedResponse[dict[str, Any]])
def list_documents(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: CurrentUserContext = Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
) -> PaginatedResponse[dict[str, Any]]:
    safe_page, safe_size, offset = paginate_params(page, page_size)
    repo = OrgScopedRepository(db, Document, current_user.organization_id)
    stmt = repo.base_query()
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(desc(Document.created_at), asc(Document.id))
            .offset(offset)
            .limit(safe_size)
        ).all()
    )
    return PaginatedResponse(
        items=[_doc_summary(d) for d in rows],
        total=total,
        page=safe_page,
        page_size=safe_size,
        total_pages=max(1, ceil(total / safe_size)) if total else 1,
    )


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    doc = OrgScopedRepository(db, Document, current_user.organization_id).get_by_id(document_id)
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status.HTTP_404_NOT_FOUND)
    summary = _doc_summary(doc)

    # Include candidate PO links when applicable
    field_map = {f["name"]: f["value"] for f in summary["fields"]}
    tot_val = None
    if field_map.get("total_amount"):
        try:
            tot_val = Decimal(str(field_map["total_amount"]))
        except Exception:
            tot_val = None
    doc_dt = None
    if field_map.get("document_date"):
        try:
            doc_dt = date.fromisoformat(str(field_map["document_date"]))
        except Exception:
            doc_dt = None
    exact_po_id, candidates, is_ambiguous = find_po_link_candidates(
        db,
        organization_id=current_user.organization_id,
        po_reference=str(field_map.get("po_reference")) if field_map.get("po_reference") else None,
        vendor_name=str(field_map.get("vendor_name")) if field_map.get("vendor_name") else None,
        total_amount=tot_val,
        doc_date=doc_dt,
    )
    summary["candidate_po_links"] = candidates
    summary["suggested_po_id"] = str(exact_po_id) if exact_po_id else None
    summary["link_ambiguous"] = is_ambiguous

    # Semantic line mapping suggestions if a PO is linked/suggested
    target_po_id = doc.transaction_id or exact_po_id
    if target_po_id and isinstance(field_map.get("line_items"), list):
        po = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id).get_by_id(
            target_po_id
        )
        if po:
            po_lines_dicts = [
                {"id": ln.id, "item_code": ln.item_code, "description": ln.description}
                for ln in po.lines
            ]
            summary["semantic_line_suggestions"] = suggest_semantic_line_mappings(
                po_lines_dicts, field_map["line_items"]
            )
    return summary


@router.get("/documents/{document_id}/file")
def download_document_file(
    document_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
) -> Response:
    doc = OrgScopedRepository(db, Document, current_user.organization_id).get_by_id(document_id)
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status.HTTP_404_NOT_FOUND)
    content = StorageAdapter().read_bytes(doc.storage_key)
    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'},
    )


@router.patch("/documents/{document_id}/fields")
def correct_extracted_fields(
    document_id: UUID,
    payload: PatchFieldsRequest,
    current_user: CurrentUserContext = Depends(require_permission("documents:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    doc = OrgScopedRepository(db, Document, current_user.organization_id).get_by_id(document_id)
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status.HTTP_404_NOT_FOUND)

    field_repo = OrgScopedRepository(db, ExtractionField, current_user.organization_id)
    changes: list[dict[str, Any]] = []
    for corr in payload.corrections:
        prev = db.scalar(
            field_repo.base_query().where(
                ExtractionField.document_id == doc.id,
                ExtractionField.field_name == corr.field_name,
                ExtractionField.is_active.is_(True),
            )
        )
        prev_val = prev.value_json.get("value") if prev else None
        next_ver = (prev.version + 1) if prev else 1
        page = prev.page if prev else 1
        bbox = prev.bbox_json if prev else None
        ev_ref = prev.evidence_ref if prev else "user:manual"
        if prev:
            prev.is_active = False

        db.add(
            ExtractionField(
                organization_id=current_user.organization_id,
                document_id=doc.id,
                field_name=corr.field_name,
                value_json={"value": corr.value},
                confidence=Decimal("1.0000"),
                page=page,
                evidence_ref=ev_ref,
                bbox_json=bbox,
                extraction_method="human_correction",
                verification_status="user_corrected",
                version=next_ver,
                is_active=True,
                corrected_by=current_user.id,
            )
        )
        changes.append({"field": corr.field_name, "before": prev_val, "after": corr.value})

    # Re-evaluate if document still has low-confidence unverified critical fields
    db.flush()
    db.refresh(doc)
    remaining_low = [
        f.field_name
        for f in doc.fields
        if f.is_active and f.verification_status == "extracted" and f.confidence < Decimal("0.80")
    ]
    if not remaining_low and doc.status == "REVIEW_REQUIRED":
        doc.status = "EXTRACTED"

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="EXTRACTION_FIELDS_CORRECTED",
        entity_type="document",
        entity_id=str(doc.id),
        after={"changes": changes},
    )
    db.commit()
    db.refresh(doc)
    return _doc_summary(doc)


@router.post("/documents/{document_id}/link")
def link_document_to_po(
    document_id: UUID,
    payload: LinkDocumentRequest,
    current_user: CurrentUserContext = Depends(require_permission("documents:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    doc = OrgScopedRepository(db, Document, current_user.organization_id).get_by_id(document_id)
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status.HTTP_404_NOT_FOUND)
    po = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id).get_by_id(
        payload.po_id
    )
    if not po:
        raise AppError("PO_NOT_FOUND", "Purchase order not found.", status.HTTP_404_NOT_FOUND)

    prev_tx = str(doc.transaction_id) if doc.transaction_id else None
    doc.transaction_id = po.id
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="DOCUMENT_LINKED_TO_PO",
        entity_type="document",
        entity_id=str(doc.id),
        before={"transaction_id": prev_tx},
        after={"transaction_id": str(po.id), "po_number": po.po_number},
    )
    db.commit()
    return {"document_id": str(doc.id), "transaction_id": str(po.id), "po_number": po.po_number}


@router.post("/documents/{document_id}/verify")
def verify_and_commit_document(
    document_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("documents:write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Commit verified extracted fields into PO, GRN, or Invoice structured records (FR-DOC-06)."""
    doc = OrgScopedRepository(db, Document, current_user.organization_id).get_by_id(document_id)
    if not doc:
        raise AppError("DOCUMENT_NOT_FOUND", "Document not found.", status.HTTP_404_NOT_FOUND)

    active_fields = [f for f in doc.fields if f.is_active]
    low_uncorrected = [
        f.field_name
        for f in active_fields
        if f.verification_status == "extracted" and f.confidence < Decimal("0.80")
    ]
    if low_uncorrected:
        raise AppError(
            code="LOW_CONFIDENCE_REVIEW_REQUIRED",
            message="Low-confidence extracted fields must be corrected/confirmed before commit.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"fields": low_uncorrected},
        )

    fmap = {f.field_name: f.value_json.get("value") for f in active_fields}
    vendor_name = str(fmap.get("vendor_name") or "Unknown Synthetic Vendor")
    vnorm = normalize_name(vendor_name)
    vendor = db.scalar(
        OrgScopedRepository(db, Vendor, current_user.organization_id)
        .base_query()
        .where(Vendor.normalized_name == vnorm)
    )
    if not vendor:
        vendor = Vendor(
            organization_id=current_user.organization_id,
            legal_name=vendor_name,
            normalized_name=vnorm,
            status="ACTIVE",
        )
        db.add(vendor)
        db.flush()

    doc_num = str(fmap.get("document_number") or f"DOC-{str(doc.id)[:8].upper()}")
    currency = str(fmap.get("currency") or "INR").upper()[:3]
    doc_dt_str = fmap.get("document_date")
    try:
        parsed_date = date.fromisoformat(str(doc_dt_str)) if doc_dt_str else date.today()
    except ValueError:
        parsed_date = date.today()

    raw_lines = fmap.get("line_items") if isinstance(fmap.get("line_items"), list) else []

    if doc.document_type == "PO":
        po_repo = OrgScopedRepository(db, PurchaseOrder, current_user.organization_id)
        existing_po = db.scalar(po_repo.base_query().where(PurchaseOrder.po_number == doc_num))
        if existing_po:
            doc.transaction_id = existing_po.id
            doc.status = "VERIFIED"
            db.commit()
            return {
                "document_id": str(doc.id),
                "entity_type": "purchase_order",
                "entity_id": str(existing_po.id),
                "transaction_id": str(existing_po.id),
            }

        total_amt = Decimal(str(fmap.get("total_amount") or "0"))
        sub_amt = Decimal(str(fmap.get("subtotal_amount") or total_amt))
        tax_amt = Decimal(str(fmap.get("tax_amount") or "0"))
        fallback_po_lines = [
            {
                "description": "PO Line",
                "quantity": "1",
                "unit_price": str(sub_amt),
                "line_total": str(total_amt),
            }
        ]
        po = PurchaseOrder(
            organization_id=current_user.organization_id,
            vendor_id=vendor.id,
            po_number=doc_num,
            issue_date=parsed_date,
            currency=currency,
            status="OPEN",
            subtotal_amount=sub_amt,
            tax_amount=tax_amt,
            total_amount=total_amt,
            document_id=doc.id,
            lines=[
                POLine(
                    organization_id=current_user.organization_id,
                    line_number=i + 1,
                    item_code=str(ln.get("item_code", "")),
                    description=str(ln.get("description", "Item")),
                    uom=str(ln.get("uom", "EA")),
                    quantity=Decimal(str(ln.get("quantity", "1"))),
                    unit_price=Decimal(str(ln.get("unit_price", "0"))),
                    tax_amount=Decimal(str(ln.get("tax_amount", "0"))),
                    line_total=Decimal(str(ln.get("line_total", "0"))),
                )
                for i, ln in enumerate(raw_lines or fallback_po_lines)
            ],
        )
        db.add(po)
        db.flush()
        doc.transaction_id = po.id
        entity_type, entity_id = "purchase_order", str(po.id)
    elif doc.document_type == "GRN":
        po_id = doc.transaction_id
        if not po_id and fmap.get("po_reference"):
            po_match = db.scalar(
                OrgScopedRepository(db, PurchaseOrder, current_user.organization_id)
                .base_query()
                .where(PurchaseOrder.po_number == str(fmap["po_reference"]))
            )
            po_id = po_match.id if po_match else None
        grn = GoodsReceipt(
            organization_id=current_user.organization_id,
            vendor_id=vendor.id,
            grn_number=doc_num,
            po_id=po_id,
            received_at=datetime.now(UTC),
            status="ACCEPTED",
            document_id=doc.id,
            lines=[
                GRNLine(
                    organization_id=current_user.organization_id,
                    item_code=str(ln.get("item_code", "")),
                    description=str(ln.get("description", "Receipt Item")),
                    received_qty=Decimal(str(ln.get("quantity", "1"))),
                    accepted_qty=Decimal(str(ln.get("quantity", "1"))),
                    rejected_qty=Decimal("0"),
                    uom=str(ln.get("uom", "EA")),
                )
                for ln in (raw_lines or [{"description": "Receipt Line", "quantity": "1"}])
            ],
        )
        db.add(grn)
        db.flush()
        doc.transaction_id = po_id or grn.id
        entity_type, entity_id = "goods_receipt", str(grn.id)
    else:
        # INVOICE (or UNKNOWN treated as invoice draft)
        po_id = doc.transaction_id
        if not po_id and fmap.get("po_reference"):
            po_match = db.scalar(
                OrgScopedRepository(db, PurchaseOrder, current_user.organization_id)
                .base_query()
                .where(PurchaseOrder.po_number == str(fmap["po_reference"]))
            )
            po_id = po_match.id if po_match else None

        norm_inv = normalize_invoice_number(doc_num)
        inv_repo = OrgScopedRepository(db, Invoice, current_user.organization_id)
        existing_dup = db.scalar(
            inv_repo.base_query().where(
                Invoice.vendor_id == vendor.id,
                Invoice.normalized_invoice_number == norm_inv,
            )
        )
        dup_of_id = existing_dup.id if existing_dup else None
        stored_norm = f"{norm_inv}__DUP__{str(uuid4())[:6]}" if existing_dup else norm_inv

        total_amt = Decimal(str(fmap.get("total_amount") or "0"))
        sub_amt = Decimal(str(fmap.get("subtotal_amount") or total_amt))
        tax_amt = Decimal(str(fmap.get("tax_amount") or "0"))
        fallback_inv_lines = [
            {
                "description": "Invoice Line",
                "quantity": "1",
                "unit_price": str(sub_amt),
                "line_total": str(total_amt),
            }
        ]
        inv = Invoice(
            organization_id=current_user.organization_id,
            vendor_id=vendor.id,
            invoice_number=doc_num,
            normalized_invoice_number=stored_norm,
            po_id=po_id,
            invoice_date=parsed_date,
            due_date=parsed_date,
            currency=currency,
            subtotal_amount=sub_amt,
            tax_amount=tax_amt,
            total_amount=total_amt,
            status="REVIEW_REQUIRED" if dup_of_id else "PENDING",
            document_id=doc.id,
            duplicate_of_invoice_id=dup_of_id,
            lines=[
                InvoiceLine(
                    organization_id=current_user.organization_id,
                    item_code=str(ln.get("item_code", "")),
                    description=str(ln.get("description", "Invoice Item")),
                    uom=str(ln.get("uom", "EA")),
                    quantity=Decimal(str(ln.get("quantity", "1"))),
                    unit_price=Decimal(str(ln.get("unit_price", str(sub_amt)))),
                    tax_amount=Decimal(str(ln.get("tax_amount", "0"))),
                    line_total=Decimal(str(ln.get("line_total", str(total_amt)))),
                )
                for ln in (raw_lines or fallback_inv_lines)
            ],
        )
        db.add(inv)
        db.flush()
        tx_id = po_id or inv.id
        doc.transaction_id = tx_id
        if dup_of_id and existing_dup is not None:
            db.add(
                RiskSignal(
                    organization_id=current_user.organization_id,
                    transaction_id=tx_id,
                    signal_type="EXACT_DUPLICATE_INVOICE",
                    severity="HIGH",
                    score=Decimal("0.9500"),
                    reason_json={
                        "reason_codes": ["EXACT_DUPLICATE_INVOICE_NUMBER"],
                        "contributing_signals": [
                            f"Matches existing invoice {existing_dup.invoice_number}"
                        ],
                        "disclaimer": "Risk indicator for review, not proof of fraud.",
                    },
                    model_version="rules-v1",
                )
            )
            db.add(
                ExceptionCase(
                    organization_id=current_user.organization_id,
                    transaction_id=tx_id,
                    type="DUPLICATE_INVOICE",
                    severity="HIGH",
                    status="OPEN",
                    summary=(
                        f"Exact duplicate invoice {doc_num} detected "
                        f"for vendor {vendor.legal_name}."
                    ),
                    affected_fields_json=["invoice_number"],
                    values_json={"invoice_number": doc_num, "duplicate_of_id": str(dup_of_id)},
                    rule_id="R-DUP-01",
                    evidence_refs_json=[{"type": "document", "id": str(doc.id)}],
                    version=1,
                )
            )
        entity_type, entity_id = "invoice", str(inv.id)

    doc.status = "VERIFIED"
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        actor_type="USER",
        actor_id=str(current_user.id),
        action="DOCUMENT_VERIFIED_COMMITTED",
        entity_type=entity_type,
        entity_id=entity_id,
        after={"document_id": str(doc.id), "transaction_id": str(doc.transaction_id)},
    )
    db.commit()
    return {
        "document_id": str(doc.id),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "transaction_id": str(doc.transaction_id),
    }


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: CurrentUserContext = Depends(require_permission("documents:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job = OrgScopedRepository(db, Job, current_user.organization_id).get_by_id(job_id)
    if not job:
        raise AppError("JOB_NOT_FOUND", "Job not found.", status.HTTP_404_NOT_FOUND)
    return {
        "job_id": str(job.id),
        "job_type": job.job_type,
        "entity_type": job.entity_type,
        "entity_id": job.entity_id,
        "status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "last_error": job.last_error,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
