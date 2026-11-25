from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.domain import Document, Job
from app.services.documents.storage import StorageAdapter
from app.workers.job_worker import process_document_job
from scripts.make_sample_docs import make_all_sample_docs
from scripts.seed import seed_synthetic_dataset


def _login_headers(client: TestClient, email: str) -> dict[str, str]:
    settings = get_settings()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.seed_default_password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_upload_validation_rejects_unsafe_and_corrupt_files(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
    headers = _login_headers(client, "operator@reconx-demo.com")

    # Double extension attack
    bad_ext = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("invoice.exe.pdf", b"%PDF-1.4\nhello", "application/pdf")},
    )
    assert bad_ext.status_code == 400
    assert bad_ext.json()["error"]["code"] == "UNSAFE_FILE_NAME"

    # MIME spoof (exe bytes disguised as .pdf)
    spoof = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("fake.pdf", b"MZ\x90\x00not_a_pdf", "application/pdf")},
    )
    assert spoof.status_code == 400
    assert spoof.json()["error"]["code"] == "MIME_MISMATCH"

    # Corrupt PDF (valid magic header, broken body)
    corrupt = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("broken.pdf", b"%PDF-1.4\ngarbage_corrupt", "application/pdf")},
    )
    assert corrupt.status_code == 400
    assert corrupt.json()["error"]["code"] == "CORRUPT_FILE"


def test_pdf_upload_extraction_duplicate_and_at07_low_confidence_gate(
    client: TestClient,
    test_db_session: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_dir))
    get_settings.cache_clear()

    seed_synthetic_dataset(test_db_session, reset=True)
    docs_dir = tmp_path / "samples"
    sample_files = {p.name: p for p in make_all_sample_docs(docs_dir)}

    headers = _login_headers(client, "operator@reconx-demo.com")

    # 1. Upload clean invoice PDF with Idempotency-Key
    pdf_bytes = sample_files["sample_invoice_at01.pdf"].read_bytes()
    up1 = client.post(
        "/api/v1/documents",
        headers={**headers, "Idempotency-Key": "idem-upload-1"},
        files={"file": ("sample_invoice_at01.pdf", pdf_bytes, "application/pdf")},
    )
    assert up1.status_code == 202
    doc_id = up1.json()["document_id"]
    job_id = up1.json()["job_id"]

    # Idempotent retry returns same document_id and job_id
    up1_retry = client.post(
        "/api/v1/documents",
        headers={**headers, "Idempotency-Key": "idem-upload-1"},
        files={"file": ("sample_invoice_at01.pdf", pdf_bytes, "application/pdf")},
    )
    assert up1_retry.status_code == 202
    assert up1_retry.json()["document_id"] == doc_id

    # Process job synchronously in test
    job = test_db_session.get(Job, __import__("uuid").UUID(job_id))
    assert job is not None
    process_document_job(test_db_session, job, storage=StorageAdapter(storage_dir))

    doc_detail = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert doc_detail.status_code == 200
    body = doc_detail.json()
    assert body["classification"] == "INVOICE"
    assert body["status"] == "EXTRACTED"
    fields = {f["name"]: f for f in body["fields"]}
    assert fields["document_number"]["value"] == "INV-BPC-9901"
    assert fields["total_amount"]["value"] == "53100.00"

    # 2. Exact duplicate file checksum detection (different idempotency key, same file bytes)
    up_dup = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("copy_invoice.pdf", pdf_bytes, "application/pdf")},
    )
    assert up_dup.status_code == 202
    assert up_dup.json()["is_duplicate_file"] is True
    assert up_dup.json()["duplicate_of_document_id"] == doc_id

    # 3. AT-07: Scanned image with low-confidence total blocks matching until corrected
    scan_bytes = sample_files["sample_scanned_invoice_at07.png"].read_bytes()
    up_scan = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("sample_scanned_invoice_at07.png", scan_bytes, "image/png")},
    )
    assert up_scan.status_code == 202
    scan_doc_id = up_scan.json()["document_id"]
    scan_job = test_db_session.get(Job, __import__("uuid").UUID(up_scan.json()["job_id"]))
    assert scan_job is not None
    process_document_job(test_db_session, scan_job, storage=StorageAdapter(storage_dir))

    scan_detail = client.get(f"/api/v1/documents/{scan_doc_id}", headers=headers).json()
    assert scan_detail["status"] == "REVIEW_REQUIRED"

    # Cannot verify/commit while low confidence remains
    blocked_verify = client.post(f"/api/v1/documents/{scan_doc_id}/verify", headers=headers)
    assert blocked_verify.status_code == 400
    assert blocked_verify.json()["error"]["code"] == "LOW_CONFIDENCE_REVIEW_REQUIRED"

    # Correct all low-confidence fields -> user_corrected -> verify succeeds
    low_names = [
        f["name"]
        for f in scan_detail["fields"]
        if f["verification_status"] == "extracted" and f["confidence"] < 0.8
    ]
    corrections = [
        {
            "field_name": fn,
            "value": next(f["value"] for f in scan_detail["fields"] if f["name"] == fn),
        }
        for fn in low_names
    ]
    if corrections:
        patch_resp = client.patch(
            f"/api/v1/documents/{scan_doc_id}/fields",
            headers=headers,
            json={"corrections": corrections},
        )
        assert patch_resp.status_code == 200
        patched_fields = {f["name"]: f for f in patch_resp.json()["fields"]}
        assert patched_fields[low_names[0]]["verification_status"] == "user_corrected"

    ok_verify = client.post(f"/api/v1/documents/{scan_doc_id}/verify", headers=headers)
    assert ok_verify.status_code == 200


def test_xlsx_grn_and_injection_invoice_and_job_failure_retry(
    client: TestClient,
    test_db_session: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_dir))
    get_settings.cache_clear()

    seed_synthetic_dataset(test_db_session, reset=True)
    sample_files = {p.name: p for p in make_all_sample_docs(tmp_path / "samples")}
    headers = _login_headers(client, "operator@reconx-demo.com")
    admin_headers = _login_headers(client, "admin@reconx-demo.com")

    # XLSX GRN parses cleanly
    xlsx_bytes = sample_files["sample_grn_at03.xlsx"].read_bytes()
    up_xlsx = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "sample_grn_at03.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert up_xlsx.status_code == 202
    xlsx_job = test_db_session.get(Job, __import__("uuid").UUID(up_xlsx.json()["job_id"]))
    assert xlsx_job is not None
    process_document_job(test_db_session, xlsx_job, storage=StorageAdapter(storage_dir))
    xlsx_doc = client.get(
        f"/api/v1/documents/{up_xlsx.json()['document_id']}", headers=headers
    ).json()
    assert xlsx_doc["classification"] == "GRN"

    # Injection invoice is parsed strictly as data; status never becomes APPROVED
    inj_bytes = sample_files["sample_injection_invoice_at08.pdf"].read_bytes()
    up_inj = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("sample_injection_invoice_at08.pdf", inj_bytes, "application/pdf")},
    )
    assert up_inj.status_code == 202
    inj_job = test_db_session.get(Job, __import__("uuid").UUID(up_inj.json()["job_id"]))
    assert inj_job is not None
    process_document_job(test_db_session, inj_job, storage=StorageAdapter(storage_dir))
    inj_doc = client.get(
        f"/api/v1/documents/{up_inj.json()['document_id']}", headers=headers
    ).json()
    assert inj_doc["classification"] == "INVOICE"
    assert inj_doc["status"] != "APPROVED"

    # Bounded job failure + admin FAILED visibility + manual retry
    doc_row = test_db_session.get(Document, __import__("uuid").UUID(inj_doc["document_id"]))
    assert doc_row is not None
    broken_job = Job(
        organization_id=doc_row.organization_id,
        job_type="PROCESS_DOCUMENT",
        entity_type="document",
        entity_id=str(doc_row.id),
        idempotency_key="force-fail-job",
        status="QUEUED",
        attempts=2,
        max_attempts=3,
    )
    test_db_session.add(broken_job)
    test_db_session.commit()

    # Use wrong storage root so read_bytes fails and triggers FAILED state
    process_document_job(test_db_session, broken_job, storage=StorageAdapter(tmp_path / "missing"))
    jobs_list = client.get("/api/v1/admin/jobs?status=FAILED", headers=admin_headers)
    assert jobs_list.status_code == 200
    assert any(j["job_id"] == str(broken_job.id) for j in jobs_list.json()["items"])

    retry_resp = client.post(f"/api/v1/admin/jobs/{broken_job.id}/retry", headers=admin_headers)
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "QUEUED"
