# Donut Challenge Implementation Plan — ReconX AI

## 1. Architecture Assessment
ReconX AI already provides:
- Pure `decimal.Decimal` 3-way reconciliation engine (`backend/app/services/reconciliation/`)
- Tenant-scoped `OrgScopedRepository` + server-side RBAC (`backend/app/core/permissions.py`)
- Immutable `audit_event` triggers (`migrations/versions/0001_foundation.py`)
- ReportLab PDF / CSV export primitives (`backend/app/api/v1/intelligence.py`)
- React + TypeScript + Tailwind + React Query + React Flow SPA (`frontend/src/`)

## 2. Files to Create & Extend

### Backend
- **Models & Migration:**
  - Create `backend/app/models/policy.py` (`Policy`, `PolicyVersion`, `PolicyEvaluation`, `PolicyAuditRun`, `ExecutiveBrief`)
  - Create `backend/migrations/versions/0003_policies_and_briefs.py`
- **Dynamic Policy Engine (`backend/app/services/policies/`):**
  - `dsl.py` — Constrained declarative rule DSL (allowlisted fields & operators, `Decimal` math, bounded nesting, zero `eval`/SQL)
  - `engine.py` — Policy lifecycle (`DRAFT -> VALIDATED -> ACTIVE -> INACTIVE -> ARCHIVED`), immutable versioning + SHA-256 content hash, dry-run impact preview, `Re-Run Audit` + idempotent `ExceptionCase` creation
  - Integrate dynamic policy evaluation into `backend/app/services/reconciliation_adapter.py`
- **Executive Brief Engine (`backend/app/services/reports/`):**
  - `executive_brief.py`, `metrics.py`, `exposure.py`, `prioritization.py`, `citations.py`, `renderers.py` (PDF via ReportLab, Markdown, CSV with formula-injection mitigation)
- **APIs & Permissions:**
  - Extend `backend/app/core/permissions.py` with `policies:*` and `reports:*` permissions
  - Create `backend/app/api/v1/policies.py` and `backend/app/api/v1/executive_briefs.py`, register in `backend/app/api/v1/router.py`
  - Seed sample active & draft policies in `backend/scripts/seed.py`

### Frontend
- Extend `frontend/src/api/client.ts`, `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx` (`INTELLIGENCE` -> `Policy Studio`, `Executive Brief`)
- Create `frontend/src/pages/PolicyStudioPage.tsx` (`/policy-studio`)
- Create `frontend/src/pages/ExecutiveBriefPage.tsx` (`/executive-brief`)
