# ReconX AI — Pitch & Architecture Outline

**Synchronise 2026 (PS-BA1): Autonomous Three-Way Invoice, Purchase Order & Goods-Receipt Reconciliation Bot**

---

## 1. The Problem: Manual AP Bottlenecks & Financial Leakage
- Accounts Payable teams reconcile PDFs, scanned images, and XLSX/CSV goods receipts across split deliveries and partial billing.
- Purely LLM-driven "AI finance" prototypes hallucinate numbers with binary floating-point arithmetic, lack multi-GRN state tracking, and are vulnerable to prompt injections hidden in vendor invoices.

## 2. The Solution: ReconX AI
- A single-backend (**FastAPI**), single-frontend (**React + TypeScript**), single-database (**PostgreSQL / SQLite**) platform implementing deterministic **three-way matching (PO vs. GRN(s) vs. Invoice(s))** paired with guarded AI assistance.
- **100% Free-Tier & Local-First Stack**: Runs fully offline with `LLM_PROVIDER=mock`, PyMuPDF + RapidOCR, and local storage, or switches via environment variable to Gemini, Groq, or Ollama free tiers.

## 3. Core Architectural Differentiators
1. **Pure Deterministic Finance Core (`decimal.Decimal` Only)**:
   - `app/services/reconciliation/` contains zero SQLAlchemy, HTTP, LLM, or `float` usage (enforced by AST tests).
   - Multi-GRN aggregation prevents double-counting while separating `ordered`, `received`, `accepted`, `rejected`, `invoiced`, `remaining_to_receive`, `eligible_to_invoice`, `over_billing`, and `under_billing`.
2. **Untrusted-Data & Prompt-Injection Defense (`AT-08`)**:
   - Every document/OCR string is fenced inside `<<<UNTRUSTED_DOCUMENT_CONTENT>>>`, tools are strictly read-only & allowlisted, and investigation findings undergo DB `evidence_ref` post-validation.
3. **Human Governance & Non-Payment Boundary**:
   - Server-side state machine (`OPEN` -> `IN_REVIEW` / `INFO_REQUESTED` / `ESCALATED` -> `APPROVED` / `REJECTED`), RBAC limits, maker-checker enforcement, optimistic locking (`409 Conflict`), and DB triggers blocking `UPDATE`/`DELETE` on `audit_event`.
   - Risk alerts and `IsolationForest` outlier flags are surfaced strictly as **risk indicators, not proof of fraud**. ReconX AI never initiates payments.

---

## 4. Measured Evaluation Results (`docs/evaluation-report.md`)
*Measured on Windows + Python 3.13 + SQLite + `LLM_PROVIDER=mock` + PyMuPDF + RapidOCR + openpyxl using deterministic synthetic data (`random.Random(20260101)` / `2026`, `random_state=42`):*

- **Dataset Scope**: **8** vendors, **40** POs, **42** invoices, **6** fresh uploaded synthetic documents; IsolationForest split **88** train (80 normal + 8 outliers) / **20** held-out test (12 normal + 8 outliers).
- **Extraction Key-Field Accuracy**: **86.96%** (20/23 fields across clean PDF, noisy PNG scan, and XLSX)
- **Reconciliation Decision Accuracy**: **100.00%** (11/11 transactions)
- **Duplicate Rule Precision / Recall**: **100.0% / 100.0%** (12 duplicate vs. distinct pairs)
- **Anomaly ML Holdout (Precision / Recall / F1 / FPR)**: **1.00 / 1.00 / 1.00 / 0.00** (20 held-out synthetic samples; non-blocking risk indicator)
- **Investigation Evidence Grounding Rate**: **100.0%** (5/5 cases resolving to DB records)
- **Document Upload + OCR/Extraction Job Latency**: **65.32 ms** P50 / **2383.79 ms** P95
- **Core Read APIs Latency (in-process `TestClient`, 60 reqs)**: **15.8 ms** P50 / **19.04 ms** P95 (`NFR-PERF-01` target < 2000 ms P95)
- **Static & Security Checks**: `ruff check`, `mypy app` (`70 source files`), `eslint`, and pytest AST/regex secret scan pass (`0` issues); `npm audit --omit=dev --audit-level=high` reports `0` high/critical production advisories.

---

## 5. Known Limitations
1. **Docker & Live PostgreSQL Execution (`OD-07`)**: Live `docker compose up` and PostgreSQL container verification were not executed on the development host because Docker Desktop was stopped; Postgres-specific Alembic triggers (`0001_foundation.py`) rely on migration/CI verification against live Postgres (`NFR-PORT-01`).
2. **External Load & Optional Security CLIs**: `locust`/`k6` concurrent external load testing and `gitleaks`/`pip-audit` host CLIs were not installed (in-process `TestClient` latency and AST secret scans were measured instead).
3. **Synthetic Corpus**: All evaluation metrics reflect synthetic invoices/GRNs and `LLM_PROVIDER=mock`; real vendor invoice scans with external LLMs will vary and should be benchmarked on domain samples before rollout.

## 6. Post-Hackathon Roadmap
- Live PostgreSQL + Docker CI pipeline running full Alembic migrations, concurrent load (`k6`/`locust`), and Playwright E2E checks.
- ERP webhook/adapter connectors (SAP/Odoo/Zoho Books) behind the same deterministic matching core while preserving human-approved posting.
- Supplier portal notifications for clarification loops (`INFO_REQUESTED`) and line-level tax rule packs (HSN/SAC GST validation).
