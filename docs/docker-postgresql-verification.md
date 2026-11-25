# ReconX AI — Docker & PostgreSQL Live Verification (`OD-07`)

**Status:** **VERIFIED** (All mandatory checks passed on live Docker Compose + PostgreSQL 16).

## 1. Environment & Versions
- **Host OS:** Windows
- **Docker Engine:** `29.9.3` (build `5457199`)
- **Docker Compose:** `v5.7.1`
- **Services (`docker-compose.yml`):**
  - `db` (`postgres:16-alpine`) — `Up (healthy)`, port `5432`
  - `backend` (`buildathon-backend`, Python 3.11-slim + FastAPI/Uvicorn) — `Up`, port `8000`
  - `frontend` (`buildathon-frontend`, Node 20-alpine + `serve -s dist -l 5173`) — `Up`, port `5173`

## 2. Migrations & Database Connectivity
`docker compose logs backend` confirmed Alembic ran cleanly against PostgreSQL (`PostgresqlImpl`):
- `Running upgrade  -> 0001_foundation, foundation auth rbac config audit`
- `Running upgrade 0001_foundation -> 0002_domain_entities, domain entities and tolerance config`
- `GET http://localhost:8000/api/v1/health` → `200 OK`: `{"status":"ok","database":"ok","version":"1.0.0"}`
- `GET http://localhost:5173/` → `200 OK`
- `docker compose exec -T backend python scripts/seed.py --reset` → `Seed complete: {'vendors': 8, 'purchase_orders': 40, 'invoices': 42}`

## 3. End-to-End Workflow Results on Live PostgreSQL
Executed against `http://localhost:8000/api/v1` backed by `postgres:16-alpine`:
- **Authentication:** `operator`, `approver`, `auditor` logged in (`200 OK`).
- **Document Upload & Extraction:** `POST /api/v1/documents` (`sample_invoice_at01.pdf`) → `202 Accepted` → `EXTRACTED`.
- **3-Way Reconciliation (`AT-02`):** `POST /api/v1/transactions/{id}/reconcile` → `EXCEPTION`.
- **7-Agent Investigation (Live Gemini):** `POST /api/v1/exceptions/{id}/investigations` → `gemini` / `gemini-2.5-flash`, `7` agents executed in `execution_trace`.
- **Evidence Graph Rebuild:** `POST /api/v1/graph/transactions/{id}/rebuild` → `11 nodes, 10 edges`.
- **Approval & Audit Trail:** `POST /api/v1/exceptions/{id}/decision` (`REJECT`) → `200 OK` (`REJECTED`); `GET /api/v1/audit` → `audit_total: 11`.

## 4. Notes
- Note that `docker compose` loads `SEED_DEFAULT_PASSWORD` from `.env` (which is `CHANGE_ME_DEMO_PASS_123!` by default from `.env.example`, or whatever value is configured in `.env`).
