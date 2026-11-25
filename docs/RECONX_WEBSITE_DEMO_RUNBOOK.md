# ReconX AI — Website Guide & Live Demo Runbook

## 1. Complete Website Page Guide (Verified Against `frontend/src/App.tsx`)

| Page & Route | Purpose | What to Click | What Happens Internally | What to Explain to Judges |
|---|---|---|---|---|
| **Login** (`/login`) | Sign in securely | Click role quick-fill or enter email + `ReconXDemo#2026!`, click **Sign in** | `POST /api/v1/auth/login` verifies Argon2 hash & issues JWT | "Six roles with server-side RBAC; operators cannot approve payments." |
| **Dashboard** (`/`) | Live operations overview | Review KPIs, BarChart, Exception Queue, Gemini card, Audit Activity | `GET /api/v1/dashboard/summary` aggregates live DB counts | "Real-time reconciliation health + Gemini status; zero hardcoded metrics." |
| **Documents** (`/documents`) | Upload & verify PO/GRN/Invoices | Drop PDF/PNG/XLSX, edit low-confidence field, click **Save** & **Verify** | `POST /api/v1/documents` -> `job_worker` (PyMuPDF/RapidOCR/openpyxl) | "Originals are immutable with SHA-256 checksums; humans fix low-confidence OCR." |
| **Transactions** (`/transactions`) | Browse & filter all POs/Invoices | Search `PO-2026-0002`, click row | `GET /api/v1/transactions` | "Every transaction tracks status, risk level, and scenario." |
| **Transaction Detail** (`/transactions/:id`) | 3-way line comparison & Evidence Graph | Click **Reconcile**, inspect `R-QTY-01` & React Flow graph | `POST /api/v1/transactions/{id}/reconcile` (`Decimal` engine) | "Shows exact line-by-line math and relational evidence graph." |
| **Exceptions** (`/exceptions`) | Queue of flagged mismatches | Filter or click an exception case | `GET /api/v1/exceptions` | "Every failed rule opens a tracked case." |
| **Exception Detail** (`/exceptions/:id`) | Investigate & approve/reject | Click **Run Investigation**, then (as Approver) submit **REJECT** with rationale | `POST /exceptions/{id}/investigations` + `POST /exceptions/{id}/decision` | "AI investigates with verified citations; only human approvers decide." |
| **Vendors** (`/vendors`) | Supplier profiles & risk history | Select a vendor | `GET /api/v1/vendors/{id}/profile` | "Tracks mismatch rate, delivery timeliness, and small-sample warnings." |
| **Cash Obligations** (`/cash`) | Due-date buckets & 30/60/90 forecast | Inspect overdue & 30/60/90 cards | `GET /api/v1/analytics/cash-obligations` | "Deterministic payables aging + run-rate projection." |
| **Agent Harness** (`/agent-harness`) | Inspect 7-stage AI + Gemini telemetry | Click agent nodes, click **Test Gemini Connection**, inspect trace | `GET /intelligence/agent-harness`, `POST /intelligence/gemini/test` | "Shows how ReconX thinks, Gemini telemetry, and `AI ≠ Authorization`." |
| **Obligation Graph** (`/obligation-graph`) | Commitment -> Delivery -> Claim graph | Switch **Obligation View** / **Evidence View**, click nodes | `GET /graph/obligations/{id}` & `/graph/transactions/{id}` | "Tracks ordered vs accepted vs invoiced exposure in PostgreSQL." |
| **Policy Studio** (`/policy-studio`) | Zero-code policy hot-swap & Re-Audit | **Create Policy** -> **Preview** -> **Activate** -> **Re-Run Audit** | `POST /policies`, `/preview`, `/activate`, `POST /policy-audits` | "Live rule updates without code edits or server restarts." |
| **Executive Brief** (`/executive-brief`) | One-click CFO brief & exports | Select scope, click **Generate Executive Brief**, export PDF/MD/CSV | `POST /executive-briefs`, `GET /executive-briefs/{id}/download` | "Top-3 urgent exceptions, `Decimal` exposure, and `CIT-*` citations." |
| **Audit Explorer** (`/audit`) | Immutable audit trail (Admin/Auditor) | Filter by action or entity | `GET /api/v1/audit` | "Append-only `audit_event` protected by DB triggers." |
| **Admin Settings** (`/admin`) | Tolerances, users, jobs (Admin) | View tolerances, config, users, jobs | `GET /admin/config`, `/tolerances`, `/users`, `/jobs` | "Configurable org tolerances and background job recovery." |

---

## 2. Demo Accounts & Safe Reset
- **URL:** `http://localhost:5173` (Docker Compose)
- **Password for all accounts:** `ReconXDemo#2026!`
  - **Admin (best for Policy Studio + Gemini Test + Brief):** `admin@reconx-demo.com`
  - **Operator (best for Upload + Reconcile + Investigation):** `operator@reconx-demo.com`
  - **Approver (best for Exception Decision):** `approver@reconx-demo.com`
  - **Auditor (read-only Audit Explorer):** `auditor@reconx-demo.com`
- **Safe Reset Command (Docker):**
  ```powershell
  docker compose exec -T backend python scripts/seed.py --reset
  ```

---

## 3. Complete 7–10 Minute Live Demo Script

| Act | Step | Where to Click | What Appears | What to Say |
|---|---|---|---|---|
| **Act 1** | 1 | Log in as `admin@reconx-demo.com` -> **Dashboard** | KPI cards, outcomes chart, Gemini card | "Companies lose money paying unverified bills. ReconX automates 3-way PO-GRN-Invoice matching." |
| **Act 2** | 2 | **Transactions** -> `PO-2026-0001` -> **Reconcile** | `MATCHED` (`100` ordered, `100` accepted, `100` invoiced) | "First, an exact match passes deterministically in `Decimal`." |
| **Act 2** | 3 | **Transactions** -> `PO-2026-0002` -> **Reconcile** | `EXCEPTION` (`R-QTY-01`: `90` accepted vs `100` billed) | "Here, 10 units are over-billed. ReconX flags ₹1,200.00 exposure automatically." |
| **Act 3** | 4 | Click exception -> **Run Investigation** | Summary, `evidence_refs`, attribution badge | "Our 7-stage harness investigates using DB-verified facts and Google Gemini." |
| **Act 3** | 5 | **Intelligence → Agent Harness** -> **Test Gemini Connection** | 7-stage React Flow, Gemini telemetry, live trace | "You see every agent, real latency, and our rule: AI recommends, humans authorize." |
| **Act 4** | 6 | **Intelligence → Obligation Graph** | `100` ordered, `90` accepted, `10` unsupported, React Flow | "Switch between Obligation View and Evidence View over the same PostgreSQL data." |
| **Act 5** | 7 | **Intelligence → Policy Studio** -> **Create Policy** (or Edit `POL-CUSTOM-QTY`) -> **Preview** -> **Activate** -> **Re-Run Audit** | Dry-run count, immutable `v1`/`v2`, Newly Flagged list | "Zero-code hot-swap: new rule goes live without restarting the backend and re-audits history." |
| **Act 6** | 8 | **Intelligence → Executive Brief** -> Select Audit Run -> **Generate Executive Brief** -> **Export PDF** | KPIs, ₹1,200.00 exposure, Top 3 exceptions, `CIT-001..`, PDF | "One click generates a boardroom brief where every number is backed by `CIT-*` citations." |
| **Act 7** | 9 | **Audit Explorer** | Immutable `audit_event` rows | "Every step—upload, match, Gemini call, policy activation, and brief—is permanently audited." |

---

## 4. 3-Minute Backup Demo (If Judges Cut Time)
1. **Dashboard** (15s): Explain problem + show Gemini card.
2. **Transaction `PO-2026-0002` → Reconcile** (30s): Show `90` vs `100` `R-QTY-01` exception.
3. **Agent Harness** (45s): Show 7 stages + Gemini telemetry + `Generated with Google Gemini` / `AI ≠ Authorization`.
4. **Policy Studio** (45s): Activate `POL-CUSTOM-QTY` → **Re-Run Audit** → show Newly Flagged.
5. **Executive Brief** (45s): Generate brief → point to `CIT-*` citations → **Export PDF**.

## 5. Actions to Avoid Live
- Do **not** upload huge (>15MB) or random external files during the timed demo; use `sample_data/` files.
- Do **not** run `seed.py --reset` mid-demo (it clears live exceptions/briefs you just created).
- Do **not** claim a `mock` fallback investigation was generated by Gemini.
