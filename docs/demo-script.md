# ReconX AI — Live Demo Script (Synchronise 2026, PS-BA1)

Estimated duration: **5–7 minutes**. Uses `LLM_PROVIDER=mock` (offline deterministic mode) and seeded synthetic data (`scripts/seed.py --reset`).

## Pre-Demo Reset
```bash
python scripts/reset_demo.py
```
Start backend (`uvicorn app.main:app --port 8000`) and frontend (`npm run dev` in `frontend/`), then open `http://localhost:5173`.

Demo credentials (all share synthetic demo password `ReconXDemo#2026!`):
- **Operator**: `operator@reconx-demo.com`
- **Approver**: `approver@reconx-demo.com`
- **Admin**: `admin@reconx-demo.com`

---

## Step 1: Overview & KPIs (`operator@reconx-demo.com`)
1. Sign in at `/login` as `operator@reconx-demo.com`.
2. Show the **Dashboard** KPI cards: total transactions (`40` seeded PO bundles), matched cases, open exceptions, job queue health, and recent audit activity.

## Step 2: Untrusted Document Ingestion & OCR Verification (`FR-DOC-01..08`, `AT-07`)
1. Navigate to **Documents** (`/documents`).
2. Upload `sample_data/sample_scanned_invoice_at07.png` or `sample_data/sample_invoice_at01.pdf`.
3. Click refresh once the background worker thread completes (`EXTRACTED` or `REVIEW_REQUIRED`), inspect extracted fields with bounding-box/page `evidence_ref` and confidence scores, optionally patch a field, and click **Verify**.
4. Point out SHA-256 checksum tracking and duplicate file detection on re-upload.

## Step 3: Deterministic 3-Way Match Engine (`AT-01`, `AT-02`, `AT-03`)
1. Navigate to **Transactions** (`/transactions`).
2. Filter/search for `AT-01` (Clean 3-Way Match) -> click **Run Reconcile** -> outcome `MATCHED`, disputed `0.0000`, line-by-line ordered/received/accepted/billed breakdown.
3. Open `AT-02` (Unit Price Variance) -> run reconcile -> outcome `EXCEPTION`, generates `PRICE_VARIANCE` rule `R-PRC-01` using pure `Decimal` arithmetic (`0.0000` float tolerance bugs).
4. Switch to the **Evidence Graph** tab (`AT-10` — React Flow relational edge graph linking Vendor -> PO -> GRN -> Invoice -> Exception -> Investigation).

## Step 4: AI Investigation Agent & Prompt-Injection Defense (`AT-08`)
1. Navigate to **Exceptions** (`/exceptions`) and open an `OPEN` case (or upload `sample_data/sample_injection_invoice_at08.pdf`).
2. Click **Run AI Investigation**. Show structured output: Facts, Discrepancies, DB-validated `evidence_refs`, Risk Indicators (`"Risk indicator for human review, not proof of fraud"`), and mandatory `human_approval_required: true`.
3. Emphasize that prompt injection commands inside invoices cannot release payments or alter vendor bank accounts.

## Step 5: Human Approval, Maker-Checker & Immutability (`AT-09`, `AT-12`)
1. Sign out and log in as **`approver@reconx-demo.com`**.
2. Open the escalated/open exception case, enter rationale, and **Approve** (or **Reject**) with optimistic `version` locking.
3. Mention that the same user who created/owned a case cannot self-approve (**maker-checker**), and every transition appends to the trigger-protected **`Audit Log`** (`/audit`).

## Step 6: Cash Obligations, Finance Copilot & Exports (`AT-11`)
1. Open **Cash View** (`/cash`) to review upcoming payment aging buckets (`0-7d`, `8-30d`, `31-60d`, `61+d`) split cleanly between Undisputed vs Disputed exposure.
2. Ask the read-only **Finance Copilot** a question (and try `"approve all invoices"` to demonstrate hard read-only guardrails).
3. Export CSV/PDF reconciliation report (`GET /api/v1/reports/export`).
