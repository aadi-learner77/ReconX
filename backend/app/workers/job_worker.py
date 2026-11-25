import threading
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.config import AppConfig
from app.models.domain import Document, ExtractionField, Job
from app.repositories.base import OrgScopedRepository
from app.services.audit.service import record_audit_event
from app.services.documents.extractor import classify_document, extract_fields_from_blocks
from app.services.documents.ocr import extract_document_blocks
from app.services.documents.storage import StorageAdapter

logger = get_logger("reconx.worker")


def enqueue_document_job(
    db: Session,
    *,
    organization_id: UUID,
    document_id: UUID,
    idempotency_key: str,
    payload: dict | None = None,
) -> Job:
    existing = db.scalar(
        OrgScopedRepository(db, Job, organization_id)
        .base_query()
        .where(Job.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    settings = get_settings()
    job = Job(
        organization_id=organization_id,
        job_type="PROCESS_DOCUMENT",
        entity_type="document",
        entity_id=str(document_id),
        idempotency_key=idempotency_key,
        status="QUEUED",
        attempts=0,
        max_attempts=settings.job_max_attempts,
        payload_json=payload or {},
    )
    db.add(job)
    db.flush()
    return job


def process_document_job(db: Session, job: Job, storage: StorageAdapter | None = None) -> Job:
    """Process one document job with bounded retries and safe failure isolation (NFR-REL-01/02)."""
    store = storage or StorageAdapter()
    job.status = "PROCESSING"
    job.attempts += 1
    job.started_at = datetime.now(UTC)
    db.commit()

    doc = db.scalar(
        OrgScopedRepository(db, Document, job.organization_id)
        .base_query()
        .where(Document.id == UUID(job.entity_id))
    )
    if not doc:
        job.status = "FAILED"
        job.last_error = "Document record not found."
        job.completed_at = datetime.now(UTC)
        db.commit()
        return job

    try:
        doc.status = "PROCESSING"
        db.commit()

        raw_bytes = store.read_bytes(doc.storage_key)
        blocks = extract_document_blocks(raw_bytes, doc.mime_type)
        full_text = "\n".join(b.text for b in blocks)
        doc.raw_text_excerpt = full_text[:2000]

        hint = (job.payload_json or {}).get("document_type_hint")
        doc_type, cls_conf = classify_document(full_text, hint=hint)
        doc.document_type = doc_type
        doc.classification_confidence = cls_conf

        candidates, val_warnings = extract_fields_from_blocks(blocks, doc_type)

        # Deactivate prior extracted fields if retrying
        old_fields = list(
            db.scalars(
                OrgScopedRepository(db, ExtractionField, job.organization_id)
                .base_query()
                .where(ExtractionField.document_id == doc.id, ExtractionField.is_active.is_(True))
            ).all()
        )
        for f in old_fields:
            f.is_active = False

        cfg = db.scalar(
            OrgScopedRepository(db, AppConfig, job.organization_id)
            .base_query()
            .where(AppConfig.is_active.is_(True))
            .order_by(desc(AppConfig.version))
        )
        conf_threshold = Decimal(
            str((cfg.config_json or {}).get("confidence_threshold", "0.80")) if cfg else "0.80"
        )

        needs_review = bool(val_warnings) or cls_conf < conf_threshold or not candidates
        for cand in candidates:
            if cand.confidence < conf_threshold:
                needs_review = True
            db.add(
                ExtractionField(
                    organization_id=job.organization_id,
                    document_id=doc.id,
                    field_name=cand.field_name,
                    value_json={"value": cand.value},
                    confidence=cand.confidence,
                    page=cand.page,
                    evidence_ref=cand.evidence_ref,
                    bbox_json=cand.bbox,
                    extraction_method=cand.extraction_method,
                    verification_status="extracted",
                    version=1,
                    is_active=True,
                )
            )

        if val_warnings:
            db.add(
                ExtractionField(
                    organization_id=job.organization_id,
                    document_id=doc.id,
                    field_name="_validation_warnings",
                    value_json={"value": val_warnings},
                    confidence=Decimal("1.0000"),
                    page=1,
                    evidence_ref="system:validator",
                    extraction_method="deterministic_validator",
                    verification_status="system_derived",
                    version=1,
                    is_active=True,
                )
            )

        doc.status = "REVIEW_REQUIRED" if needs_review else "EXTRACTED"
        job.status = "SUCCEEDED"
        job.last_error = None
        job.completed_at = datetime.now(UTC)

        record_audit_event(
            db,
            organization_id=job.organization_id,
            actor_type="SYSTEM",
            actor_id="job_worker",
            action="DOCUMENT_PROCESSED",
            entity_type="document",
            entity_id=str(doc.id),
            after={
                "document_type": doc.document_type,
                "status": doc.status,
                "field_count": len(candidates),
                "warnings": val_warnings,
            },
        )
        db.commit()
        return job

    except Exception as exc:
        db.rollback()
        # Re-load after rollback so original document stays intact and status reflects failure
        job_row = db.get(Job, job.id)
        doc_row = db.get(Document, doc.id)
        if job_row:
            job_row.last_error = str(exc)[:1000]
            if job_row.attempts < job_row.max_attempts:
                job_row.status = "QUEUED"
            else:
                job_row.status = "FAILED"
                job_row.completed_at = datetime.now(UTC)
                if doc_row:
                    doc_row.status = "FAILED"
            record_audit_event(
                db,
                organization_id=job.organization_id,
                actor_type="SYSTEM",
                actor_id="job_worker",
                action="DOCUMENT_PROCESSING_FAILED",
                entity_type="job",
                entity_id=str(job.id),
                after={
                    "attempts": job_row.attempts,
                    "status": job_row.status,
                    "error": job_row.last_error,
                },
            )
            db.commit()
            return job_row
        return job


class BackgroundJobWorker:
    """In-process daemon worker thread polling DB jobs table (Decision D1)."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="reconx-job-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _run_loop(self) -> None:
        settings = get_settings()
        while not self._stop_event.is_set():
            processed_any = False
            try:
                with SessionLocal() as db:
                    next_job = db.scalar(
                        select(Job)
                        .where(Job.status == "QUEUED")
                        .order_by(asc(Job.created_at))
                        .limit(1)
                    )
                    if next_job is not None:
                        process_document_job(db, next_job)
                        processed_any = True
            except Exception as exc:
                logger.error("worker_loop_error", extra={"extra_fields": {"error": str(exc)}})
            if not processed_any:
                self._stop_event.wait(settings.worker_poll_interval_seconds)


background_worker = BackgroundJobWorker()
