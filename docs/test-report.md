# ReconX AI — Test Execution Report

## 1. Backend Automated Test Suites (`pytest`)
- **Latest Run (after Phase 2–5 + EvidenceGraphAgent updates):**
  - `backend/.venv/Scripts/pytest.exe -v`
  - Includes:
    - `test_admin_config.py` (config & tolerance CRUD + audit)
    - `test_audit.py` (immutable `audit_event` DB triggers)
    - `test_auth_rbac.py` (Argon2, JWT refresh/logout, 6-role RBAC)
    - `test_document_pipeline.py` (PyMuPDF, RapidOCR, openpyxl, checksum dedup, human verify)
    - `test_domain_records.py` (PO/GRN/Invoice persistence)
    - `test_hardening_security.py` (cross-tenant IDOR sweep, AST pure-Decimal boundary scan, no-secrets scan)
    - `test_intelligence_and_p2.py` (`AT-08` prompt injection, `AT-10` graph feature flag, `AT-11` copilot tenant isolation, exports)
    - `test_reconciliation_api.py` (`AT-01..AT-06` API matching)
    - `test_reconciliation_engine.py` (pure `Decimal` & Hypothesis property tests)
    - `test_srs_gap_closure.py` (7-agent `execution_trace`, `SPLIT_INVOICE_PATTERN`, `SHARED_BANK_ACCOUNT`, `forecast_30_60_90`, structured Copilot tools, Evidence Graph history & rebuild)
    - `test_workflow_approvals.py` (`AT-09`, `AT-12` maker-checker & optimistic locking)

## 2. Static Analysis & Type Safety
- **Ruff (`ruff check app tests scripts`):** `All checks passed!`
- **Mypy (`mypy app`):** `Success: no issues found in 71 source files`

## 3. Frontend Verification (`frontend/`)
- **ESLint (`npm run lint`):** Passed (`0` errors)
- **Vitest (`npm test`):** `1` file, `3 passed` (`src/__tests__/components.test.tsx`)
- **Production Build (`npm run build`):** `tsc && vite build` succeeded (`built in 6.48s`)

## 4. Live AI Provider & Fallback Verification
- Tested `get_llm_provider()` with `LLM_PROVIDER=gemini` and `GeminiLLMProvider('invalid_key', ...)` fallback: both `classify` and `explain` handled provider errors gracefully via deterministic fallback with zero exceptions.

## 5. Pending / Environment-Blocked Checks
- **Docker Compose / Live PostgreSQL (`OD-07`):** `NOT VERIFIED` locally because Docker Desktop daemon is not running on this Windows host.
