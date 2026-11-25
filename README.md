# ReconX AI — Autonomous Three-Way Invoice, PO & Goods-Receipt Reconciliation Bot

**Synchronise 2026 | Problem Statement PS-BA1 | SRS `RXAI-SRS-001 v1.0`**

ReconX AI automates Purchase Order (PO), Goods Receipt Note (GRN), and Vendor Invoice three-way reconciliation on a **100% free stack** (FastAPI + React/TypeScript + PostgreSQL/SQLite + PyMuPDF + RapidOCR), combining a **pure-Python `decimal.Decimal` matching engine** with guarded, human-in-the-loop AI extraction and case investigation.

## Key Capabilities
- **Deterministic Three-Way Reconciliation Engine** (`backend/app/services/reconciliation/`): Pure Python `decimal.Decimal` + DB `NUMERIC(18,4)` arithmetic (zero `float`), covering header/supplier/currency/duplicate checks, line-level PO vs GRN accepted vs invoiced quantities, partial deliveries, split invoices, UOM checks, price/tax tolerance evaluation, and automated undisputed vs disputed splits.
- **Untrusted Document Ingestion & OCR** (`backend/app/services/documents/`): Accepts digital PDFs (PyMuPDF text layer), scanned PDFs/PNG/JPGs (RapidOCR `onnxruntime`), and XLSX/CSV spreadsheets (`openpyxl`), with magic-byte MIME validation, SHA-256 checksum deduplication, field-level confidence gating (`REVIEW_REQUIRED`), and manual verify/patch workflows.
- **DB-Backed Asynchronous Job Worker** (`backend/app/workers/job_worker.py`): Idempotent `job` table + in-process daemon worker thread (`QUEUED` -> `PROCESSING` -> `SUCCEEDED` / `FAILED`) with bounded retries and admin retry endpoint.
- **Guardrailed AI Investigation & Read-Only Finance Copilot** (`backend/app/services/agents/`): `LLMProvider` adapter (`mock` default offline, `gemini`, `groq`, `ollama`), allowlisted read/draft tools only, untrusted delimiter wrapping, Pydantic schema enforcement, and DB-resolvable `evidence_ref` post-validation. LLMs never approve, match, or trigger payments.
- **Risk Indicators, Workflows & Immutable Audit** (`backend/app/services/risk/`, `workflows/`, `audit/`): Near-duplicate detection, MAD robust z-score price spikes, enhanced verification for bank-detail changes, IsolationForest outlier indicators (`"Risk indicator for human review, not proof of fraud"`), maker-checker RBAC, approval tiers, and trigger-enforced append-only `audit_event`.
- **Interactive Frontend** (`frontend/`): React + TypeScript + Vite + Tailwind CSS + TanStack Query + Recharts + React Flow Financial Evidence Graph.

---

## Documentation
- [Source of Truth SRS](docs/SRS.md)
- [Architecture & Trust Boundaries](docs/architecture.md)
- [Decisions & Open Decisions (`D1`–`D9`, `OD-01`–`OD-07`)](docs/DECISIONS.md)
- [Requirements Traceability Matrix](docs/requirements-traceability.md)
- [API Contracts](docs/api-contracts.md) & [ERD](docs/erd.md) & [Threat Model](docs/threat-model.md)
- [Measured Evaluation Report](docs/evaluation-report.md)
- [Deployment Guide (Docker & Free Cloud)](docs/deployment.md)
- [Live Demo Script](docs/demo-script.md) & [Pitch Outline](docs/pitch-outline.md)

---

## Quickstart (Local Bare-Metal / Windows / Linux)

1. Copy `.env.example` to `.env` (optional for local default SQLite/dev, required if overriding secrets or cloud URLs):
   ```bash
   cp .env.example .env
   ```

2. Backend setup & synthetic seed (local SQLite mode without Postgres):
   ```bash
   cd backend
   python -m venv .venv
   # Windows PowerShell: .venv\Scripts\activate  | Linux/macOS: source .venv/bin/activate
   pip install -e ".[dev]"
   # PowerShell: $env:DATABASE_URL="sqlite:///./reconx_demo.db"
   # Bash:       export DATABASE_URL="sqlite:///./reconx_demo.db"
   python scripts/seed.py --reset
   python scripts/make_sample_docs.py
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

3. Frontend setup:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://127.0.0.1:5173`.

## Quickstart (Docker Compose)
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py --reset
```

## Synthetic Demo Accounts
All seeded synthetic users share default password `ReconXDemo#2026!` (override via `SEED_DEFAULT_PASSWORD` env var):
- `operator@reconx-demo.com` (Finance Operator)
- `approver@reconx-demo.com` (Finance Approver)
- `procurement@reconx-demo.com` (Procurement)
- `receiving@reconx-demo.com` (Receiving)
- `auditor@reconx-demo.com` (Auditor — read-only + audit log access)
- `admin@reconx-demo.com` (Admin — config, tolerances, users, job retry)

---

## Verification & Evaluation Commands
```bash
# Backend lint, types & tests (36 tests incl. Hypothesis + security/IDOR/prompt-injection/resilience)
cd backend
ruff check app tests scripts
mypy app
pytest -v

# Quantitative Evaluation Benchmark (updates docs/evaluation-report.md from measured runs)
python scripts/run_evaluation.py

# Frontend build, lint & Vitest component tests
cd ../frontend
npm run build
npm run lint
npm test

# End-to-End Playwright Smoke Test (orchestrates seed + backend + Vite + Chromium)
cd ../backend
python scripts/run_e2e.py
```
