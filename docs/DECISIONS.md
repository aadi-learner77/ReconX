# Architecture & Product Decisions — ReconX AI

Source of truth: `docs/SRS.md` (RXAI-SRS-001 v1.0). All deviations from SRS defaults and open decisions are tracked here.

## Fixed Technical Decisions (D1–D9)

| ID | Topic | Decision | Rationale & SRS Mapping |
|---|---|---|---|
| **D1** | Background Jobs | DB-backed `jobs` table + in-process worker thread (`QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED`), idempotency key, bounded retries, visible `FAILED` state. | Simplest viable free architecture without Redis/Celery; satisfies SRS 2.2 ("equivalent task queue"), NFR-PERF-02, NFR-REL-02. |
| **D2** | Financial Evidence Graph | Relational edge queries over PostgreSQL + React Flow UI; no Neo4j service. | SRS 8.4 explicitly marks graph optional and states PostgreSQL remains source of truth. Avoids extra infrastructure. |
| **D3** | LLM Provider Adapter | `LLMProvider` interface with `mock` (default, local fixtures), `gemini` (free API key), `groq` (free API key), `ollama` (local). Selected via `LLM_PROVIDER` env var. | Core matching and demo work offline with `mock` and zero paid services; optional free-tier live LLM upgrade. |
| **D4** | OCR & Document Parsing | PyMuPDF (`fitz`) text layer extraction first; RapidOCR (`onnxruntime`) fallback for scanned PDFs/images; `openpyxl`/`pandas` for XLSX/CSV. | 100% free local execution without paid OCR APIs or heavy PaddlePaddle runtime. |
| **D5** | Authentication & Passwords | Self-hosted JWT (short-lived access + refresh tokens, HS256) with `argon2-cffi` password hashing and server-side RBAC. | Zero paid auth SaaS dependencies; satisfies FR-AUTH-01..03 and NFR-SEC-01. |
| **D6** | Document Storage | Local disk directory outside web root behind a `StorageAdapter` interface using random UUID storage keys and SHA-256 checksums. | Immutable originals, portable in Docker volume, replaceable later with S3/R2 without changing domain code. |
| **D7** | Frontend Stack | React + TypeScript + Vite + Tailwind CSS + TanStack Query + React Router + Recharts + React Flow. | Clean modern typed SPA; satisfies SRS 2.2 and 9.1. |
| **D8** | Testing Stack | `pytest` (+ `hypothesis` property tests), `Vitest` (component tests), `Playwright` (E2E smoke). | Automated verification across deterministic rules, API contracts, UI components, and full user flows. |
| **D9** | Deployment Targets | Local: Docker Compose (`db`, `backend`, `frontend`). Cloud (free tier): Vercel/Netlify (frontend), Render free web service (backend), Neon/Supabase free Postgres. | Free hosting options; check current provider limits in `docs/deployment.md` before relying on them. |

---

## Open Decisions (from SRS Section 17.2 + Environment Findings)

| ID | Open Question (SRS 17.2 / Runtime) | Proposed Default | Status |
|---|---|---|---|
| **OD-01** | Official hackathon constraints: mandatory technology, offline/online requirements, judging rubric and submission format. | Use standard web stack (FastAPI + React + Postgres) with offline-safe `LLM_PROVIDER=mock` default and Docker Compose local delivery. | OPEN (confirm with organizers) |
| **OD-02** | Whether email inbox ingestion or ERP integration is expected by the organisers. | Simulate via manual file upload (`POST /api/v1/documents`) and structured JSON/seed import; keep `IntegrationAdapter` clean for later connectors (SRS 9.3). | PROPOSED DEFAULT ADOPTED |
| **OD-03** | Supported document formats and maximum file size. | Support `PDF`, `PNG`, `JPG/JPEG`, `XLSX`, `CSV` (per FR-DOC-01) with configurable `MAX_UPLOAD_SIZE_MB=15` and magic-byte validation. | PROPOSED DEFAULT ADOPTED |
| **OD-04** | Whether services, milestone billing, advance payments, credit notes and debit notes are required. | Core focuses on goods three-way match (`PO` + `GRN` + `Invoice`), partial deliveries across multiple GRNs, and split invoices. Service/advance policy toggle exists in `tolerance_config`, credit/debit notes deferred. | PROPOSED DEFAULT ADOPTED |
| **OD-05** | Organization-specific tolerances, tax rules, approval hierarchy and retention policy. | Configurable per-organization `tolerance_config` & `app_config` (demo default: 2% price tolerance, 0% quantity over-billing tolerance, INR/GST synthetic data without hardcoding INR/GST into engine). | PROPOSED DEFAULT ADOPTED |
| **OD-06** | Whether the team can use external LLM/OCR APIs and whether data may leave the local environment. | Default `LLM_PROVIDER=mock` and local PyMuPDF/RapidOCR so zero data leaves localhost; synthetic data only if Gemini/Groq free APIs are enabled. | PROPOSED DEFAULT ADOPTED |
| **OD-07** | Local Docker Desktop / PostgreSQL daemon availability during development environment build. | Docker Desktop daemon is currently stopped (`//./pipe/dockerDesktopLinuxEngine` not available) and native `psql` is absent on this Windows host. Backend ORM and migrations target PostgreSQL (`NUMERIC(18,4)`, `UUID`, `audit_event` immutability triggers), while automated test suites verify dialect-compatible SQLAlchemy schemas + SQLite triggers locally until Docker Compose is started against live PostgreSQL. | OPEN (verify live Docker/Postgres once Docker Desktop is started) |
