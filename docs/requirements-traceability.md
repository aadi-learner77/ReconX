# Requirements Traceability Matrix — ReconX AI

Source of Truth: `docs/SRS.md` (`RXAI-SRS-001 v1.0`).
Status values: `NOT_STARTED` | `IN_PROGRESS` | `IMPLEMENTED` | `DEFERRED`.

## Functional Requirements (FR)

| ID | Priority | Module | API Endpoint | Test File | Status |
|---|---|---|---|---|---|
| FR-AUTH-01 | P0 | `backend/app/api/v1/auth.py`, `core/security.py` | `POST /api/v1/auth/login`, `/refresh`, `/logout` | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| FR-AUTH-02 | P0 | `backend/app/core/permissions.py` | All protected `/api/v1/*` routes | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| FR-AUTH-03 | P0 | `backend/app/models/auth.py` | `GET /api/v1/auth/me`, `POST /api/v1/admin/users` | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| FR-AUTH-04 | P1 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision`, `PUT /api/v1/admin/config` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-AUTH-05 | P0 | `backend/app/services/audit/` | All mutating `/api/v1/*` routes | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-CFG-01 | P0 | `backend/app/api/v1/admin.py`, `models/config.py` | `GET/PUT /api/v1/admin/config`, `/tolerances` | `backend/tests/test_admin_config.py`, `test_domain_records.py` | IMPLEMENTED |
| FR-CFG-02 | P1 | `backend/app/models/config.py`, `services/audit/` | `PUT /api/v1/admin/config`, `GET /api/v1/audit` | `backend/tests/test_admin_config.py` | IMPLEMENTED |
| FR-DOC-01 | P0 | `backend/app/api/v1/documents.py`, `services/documents/` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-02 | P0 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-03 | P0 | `backend/app/models/domain.py`, `services/documents/storage.py` | `POST /api/v1/documents`, `GET /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-04 | P0 | `backend/app/api/v1/documents.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-05 | P0 | `backend/app/services/documents/ocr.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-06 | P0 | `backend/app/api/v1/documents.py` | `PATCH /api/v1/documents/{id}/fields`, `POST /api/v1/documents/{id}/verify` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-07 | P1 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-DOC-08 | P0 | `backend/app/services/documents/validation.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-EXT-01 | P0 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-EXT-02 | P0 | `backend/app/models/domain.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-EXT-03 | P0 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-EXT-04 | P0 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-EXT-05 | P1 | `backend/app/services/documents/linker.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-EXT-06 | P0 | `backend/app/services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-EXT-07 | P0 | `backend/app/models/domain.py` | `PATCH /api/v1/documents/{id}/fields` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-MAT-01 | P0 | `backend/app/services/documents/linker.py` | `POST /api/v1/documents/{id}/link` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| FR-MAT-02 | P0 | `backend/app/services/reconciliation/engine.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-03 | P0 | `backend/app/services/reconciliation/engine.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-04 | P1 | `backend/app/services/reconciliation/engine.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-05 | P0 | `backend/app/services/reconciliation/quantities.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-06 | P0 | `backend/app/services/reconciliation/rules.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-07 | P0 | `backend/app/services/reconciliation/rules.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-08 | P0 | `backend/app/services/reconciliation/engine.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-MAT-09 | P0 | `backend/app/services/reconciliation/engine.py`, `services/workflows/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-EXC-01 | P0 | `backend/app/services/exceptions/` | `GET /api/v1/exceptions` | `backend/tests/test_reconciliation_api.py` | IMPLEMENTED |
| FR-EXC-02 | P0 | `backend/app/models/exception.py` | `GET /api/v1/exceptions/{id}` | `backend/tests/test_reconciliation_api.py` | IMPLEMENTED |
| FR-EXC-03 | P1 | `backend/app/services/agents/investigator.py` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-EXC-04 | P1 | `backend/app/services/agents/investigator.py` | `GET /api/v1/investigations/{id}` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-EXC-05 | P1 | `backend/app/services/agents/investigator.py` | `GET /api/v1/investigations/{id}` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-EXC-06 | P0 | `backend/app/services/agents/investigator.py` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-EXC-07 | P0 | `backend/app/services/agents/tools.py` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-EXC-08 | P0 | `backend/app/api/v1/exceptions.py` | `POST /api/v1/exceptions/{id}/assign`, `/comments`, `/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-EXC-09 | P0 | `backend/app/services/agents/tools.py`, `services/audit/` | `GET /api/v1/audit` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-01 | P0 | `backend/app/services/reconciliation/rules.py`, `services/risk/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-RISK-02 | P1 | `backend/app/services/risk/engine.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-03 | P1 | `backend/app/services/risk/engine.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-04 | P1 | `backend/app/services/risk/engine.py` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-05 | P1 | `backend/app/models/domain.py`, `services/risk/engine.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-06 | P0 | `backend/app/services/risk/engine.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-07 | P0 | `backend/app/services/risk/engine.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-RISK-08 | P0 | `backend/app/services/risk/engine.py`, `api/v1/intelligence.py` | `POST /api/v1/vendors/{id}/bank-change` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-VEN-01 | P1 | `backend/app/services/risk/engine.py` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-VEN-02 | P1 | `backend/app/services/risk/engine.py` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-VEN-03 | P2 | `backend/app/services/risk/engine.py` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-VEN-04 | P0 | `backend/app/services/risk/engine.py` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-WF-01 | P0 | `backend/app/services/workflows/state_machine.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-WF-02 | P0 | `backend/app/api/v1/exceptions.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-WF-03 | P0 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-WF-04 | P1 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-WF-05 | P0 | `backend/app/models/domain.py`, `services/audit/` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-WF-06 | P0 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-UI-01 | P0 | `frontend/src/pages/DashboardPage.tsx`, `api/v1/intelligence.py` | `GET /api/v1/dashboard/summary` | `frontend/src/__tests__/components.test.tsx`, `e2e/smoke.spec.ts` | IMPLEMENTED |
| FR-UI-02 | P0 | `frontend/src/pages/TransactionsPage.tsx`, `api/v1/transactions.py` | `GET /api/v1/transactions` | `frontend/e2e/smoke.spec.ts` | IMPLEMENTED |
| FR-UI-03 | P0 | `frontend/src/pages/TransactionDetailPage.tsx` | `GET /api/v1/transactions/{id}` | `frontend/src/__tests__/components.test.tsx`, `e2e/smoke.spec.ts` | IMPLEMENTED |
| FR-UI-04 | P1 | `backend/app/api/v1/intelligence.py` | `GET /api/v1/analytics/cash-obligations` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-UI-05 | P1 | `backend/app/services/agents/copilot.py`, `api/v1/intelligence.py` | `POST /api/v1/copilot/query` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-UI-06 | P1 | `backend/app/services/agents/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-UI-07 | P0 | `backend/app/services/agents/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-UI-08 | P1 | `backend/app/api/v1/intelligence.py` | `GET /api/v1/reports/export` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| FR-AUD-01 | P0 | `backend/app/services/audit/service.py` | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-AUD-02 | P0 | `backend/app/models/audit.py` | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-AUD-03 | P0 | `backend/migrations/` (DB trigger) | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-NOT-01 | P1 | `backend/app/services/workflows/approval.py`, `api/v1/exceptions.py` | `GET /api/v1/notifications` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| FR-NOT-02 | P0 | `backend/app/services/workflows/approval.py`, `api/v1/exceptions.py` | `GET /api/v1/notifications` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |

## Non-Functional Requirements (NFR)

| ID | Priority | Module | API Endpoint | Test File | Status |
|---|---|---|---|---|---|
| NFR-PERF-01 | P1 | `backend/app/main.py` | `GET /api/v1/dashboard/summary`, `/transactions` | `backend/tests/test_performance.py` | NOT_STARTED |
| NFR-PERF-02 | P0 | `backend/app/workers/job_worker.py` | `POST /api/v1/documents`, `GET /api/v1/jobs/{id}` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| NFR-REL-01 | P0 | `backend/app/workers/job_worker.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| NFR-REL-02 | P0 | `backend/app/models/domain.py`, `api/v1/admin.py` | `GET /api/v1/admin/jobs`, `POST /api/v1/admin/jobs/{id}/retry` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| NFR-SEC-01 | P0 | `backend/app/core/security.py` | `POST /api/v1/auth/login` | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| NFR-SEC-02 | P0 | `.env.example`, `backend/app/core/config.py` | N/A | `backend/tests/test_security_sweep.py` | IMPLEMENTED |
| NFR-SEC-03 | P0 | `backend/app/repositories/base.py`, `core/permissions.py` | All `/api/v1/*` | `backend/tests/test_security_sweep.py` | IMPLEMENTED |
| NFR-AUD-01 | P0 | `backend/app/services/audit/service.py` | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| NFR-MAINT-01 | P0 | `backend/app/services/*` | N/A | `backend/tests/test_architecture_boundaries.py` | NOT_STARTED |
| NFR-TEST-01 | P0 | `backend/app/services/reconciliation/` | N/A | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| NFR-SCALE-01 | P1 | `backend/app/workers/job_worker.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| NFR-UX-01 | P1 | `frontend/src/*` | N/A | `frontend/e2e/smoke.spec.ts` | IMPLEMENTED |
| NFR-PORT-01 | P1 | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | `GET /api/v1/health` | `docs/deployment.md` | NOT_STARTED |
| NFR-OBS-01 | P0 | `backend/app/core/logging.py`, `middleware.py` | All `/api/v1/*` | `backend/tests/test_security_sweep.py` | IMPLEMENTED |

## Minimum Acceptance Scenarios (AT)

| ID | Priority | Module | API Endpoint | Test File | Status |
|---|---|---|---|---|---|
| AT-01 | P0 | `services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_api.py`, `test_reconciliation_engine.py` | IMPLEMENTED |
| AT-02 | P0 | `services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_api.py`, `test_reconciliation_engine.py` | IMPLEMENTED |
| AT-03 | P0 | `services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_api.py`, `test_reconciliation_engine.py` | IMPLEMENTED |
| AT-04 | P0 | `services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_api.py`, `test_reconciliation_engine.py` | IMPLEMENTED |
| AT-05 | P0 | `services/reconciliation/`, `services/risk/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_api.py`, `test_reconciliation_engine.py` | IMPLEMENTED |
| AT-06 | P0 | `services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_api.py`, `test_reconciliation_engine.py` | IMPLEMENTED |
| AT-07 | P0 | `services/documents/` | `GET /api/v1/documents/{id}`, `POST /api/v1/documents/{id}/verify` | `backend/tests/test_document_pipeline.py` | IMPLEMENTED |
| AT-08 | P0 | `services/agents/` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| AT-09 | P0 | `api/v1/exceptions.py`, `core/permissions.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
| AT-10 | P0 | `services/graph/`, `services/reconciliation/` | `GET /api/v1/graph/transactions/{id}`, `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| AT-11 | P0 | `services/agents/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_intelligence_and_p2.py` | IMPLEMENTED |
| AT-12 | P0 | `services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | IMPLEMENTED |
