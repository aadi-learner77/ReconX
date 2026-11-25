# Requirements Traceability Matrix — ReconX AI

Source of Truth: `docs/SRS.md` (`RXAI-SRS-001 v1.0`).
Status values: `NOT_STARTED` | `IN_PROGRESS` | `IMPLEMENTED` | `DEFERRED`.

## Functional Requirements (FR)

| ID | Priority | Module | API Endpoint | Test File | Status |
|---|---|---|---|---|---|
| FR-AUTH-01 | P0 | `backend/app/api/v1/auth.py`, `core/security.py` | `POST /api/v1/auth/login`, `/refresh`, `/logout` | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| FR-AUTH-02 | P0 | `backend/app/core/permissions.py` | All protected `/api/v1/*` routes | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| FR-AUTH-03 | P0 | `backend/app/models/auth.py` | `GET /api/v1/auth/me`, `POST /api/v1/admin/users` | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| FR-AUTH-04 | P1 | `backend/app/services/workflows/` | `POST /api/v1/exceptions/{id}/decision`, `PUT /api/v1/admin/config` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-AUTH-05 | P0 | `backend/app/services/audit/` | All mutating `/api/v1/*` routes | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-CFG-01 | P0 | `backend/app/api/v1/admin.py`, `models/config.py` | `GET/PUT /api/v1/admin/config`, `/tolerances` | `backend/tests/test_admin_config.py`, `test_domain_records.py` | IMPLEMENTED |
| FR-CFG-02 | P1 | `backend/app/models/config.py`, `services/audit/` | `PUT /api/v1/admin/config`, `GET /api/v1/audit` | `backend/tests/test_admin_config.py` | IMPLEMENTED |
| FR-DOC-01 | P0 | `backend/app/api/v1/documents.py`, `services/documents/` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-02 | P0 | `backend/app/services/documents/classifier.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-03 | P0 | `backend/app/models/document.py`, `services/documents/storage.py` | `POST /api/v1/documents`, `GET /api/v1/documents` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-04 | P0 | `backend/app/services/documents/ingestion.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-05 | P0 | `backend/app/services/documents/ocr.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-06 | P0 | `backend/app/api/v1/documents.py` | `PATCH /api/v1/documents/{id}/fields`, `POST /api/v1/documents/{id}/verify` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-07 | P1 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-DOC-08 | P0 | `backend/app/services/documents/validation.py` | `POST /api/v1/documents` | `backend/tests/test_security_uploads.py` | NOT_STARTED |
| FR-EXT-01 | P0 | `backend/app/services/documents/extractor.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-EXT-02 | P0 | `backend/app/models/document.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-EXT-03 | P0 | `backend/app/services/documents/field_validator.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-EXT-04 | P0 | `backend/app/services/documents/field_validator.py` | `GET /api/v1/documents/{id}` | `backend/tests/test_acceptance.py` | NOT_STARTED |
| FR-EXT-05 | P1 | `backend/app/services/documents/linker.py` | `GET /api/v1/documents/{id}/candidates` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-EXT-06 | P0 | `backend/app/services/reconciliation/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-EXT-07 | P0 | `backend/app/models/document.py` | `PATCH /api/v1/documents/{id}/fields` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| FR-MAT-01 | P0 | `backend/app/services/documents/linker.py` | `POST /api/v1/documents/{id}/link` | `backend/tests/test_document_pipeline.py` | IN_PROGRESS |
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
| FR-EXC-03 | P1 | `backend/app/services/agents/investigator.py` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_investigation_agent.py` | NOT_STARTED |
| FR-EXC-04 | P1 | `backend/app/services/agents/investigator.py` | `GET /api/v1/investigations/{id}` | `backend/tests/test_investigation_agent.py` | NOT_STARTED |
| FR-EXC-05 | P1 | `backend/app/services/agents/schemas.py` | `GET /api/v1/investigations/{id}` | `backend/tests/test_investigation_agent.py` | NOT_STARTED |
| FR-EXC-06 | P0 | `backend/app/services/agents/validator.py` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_investigation_agent.py` | NOT_STARTED |
| FR-EXC-07 | P0 | `backend/app/services/agents/tools.py` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_security_agent.py` | NOT_STARTED |
| FR-EXC-08 | P0 | `backend/app/api/v1/exceptions.py` | `POST /api/v1/exceptions/{id}/assign`, `/comments`, `/decision` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-EXC-09 | P0 | `backend/app/services/agents/tools.py`, `services/audit/` | `GET /api/v1/audit` | `backend/tests/test_investigation_agent.py` | NOT_STARTED |
| FR-RISK-01 | P0 | `backend/app/services/reconciliation/rules.py`, `services/risk/` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| FR-RISK-02 | P1 | `backend/app/services/risk/duplicates.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-RISK-03 | P1 | `backend/app/services/risk/price_anomaly.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-RISK-04 | P1 | `backend/app/services/risk/vendor_patterns.py` | `GET /api/v1/vendors/{id}` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-RISK-05 | P1 | `backend/app/models/risk.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-RISK-06 | P0 | `backend/app/services/risk/`, `frontend/src/components/` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-RISK-07 | P0 | `backend/app/services/risk/ml_anomaly.py` | `GET /api/v1/transactions/{id}/risk` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-RISK-08 | P0 | `backend/app/services/risk/`, `services/workflows/` | `POST /api/v1/vendors/{id}/bank-change` | `backend/tests/test_risk_service.py` | NOT_STARTED |
| FR-VEN-01 | P1 | `backend/app/services/vendors/` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_vendors.py` | NOT_STARTED |
| FR-VEN-02 | P1 | `backend/app/services/vendors/` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_vendors.py` | NOT_STARTED |
| FR-VEN-03 | P2 | `backend/app/services/vendors/` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_vendors.py` | NOT_STARTED |
| FR-VEN-04 | P0 | `backend/app/services/vendors/` | `GET /api/v1/vendors/{id}/profile` | `backend/tests/test_vendors.py` | NOT_STARTED |
| FR-WF-01 | P0 | `backend/app/services/workflows/state_machine.py` | `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-WF-02 | P0 | `backend/app/api/v1/exceptions.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-WF-03 | P0 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-WF-04 | P1 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-WF-05 | P0 | `backend/app/models/approval.py`, `services/audit/` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-WF-06 | P0 | `backend/app/services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_workflow_approvals.py` | NOT_STARTED |
| FR-UI-01 | P0 | `frontend/src/pages/DashboardPage.tsx`, `api/v1/dashboard.py` | `GET /api/v1/dashboard/summary` | `frontend/src/__tests__/Dashboard.test.tsx` | NOT_STARTED |
| FR-UI-02 | P0 | `frontend/src/pages/TransactionsPage.tsx`, `api/v1/transactions.py` | `GET /api/v1/transactions` | `frontend/e2e/smoke.spec.ts` | NOT_STARTED |
| FR-UI-03 | P0 | `frontend/src/pages/TransactionDetailPage.tsx` | `GET /api/v1/transactions/{id}` | `frontend/src/__tests__/DiffTable.test.tsx` | NOT_STARTED |
| FR-UI-04 | P1 | `frontend/src/pages/CashViewPage.tsx`, `api/v1/analytics.py` | `GET /api/v1/analytics/cash-obligations` | `backend/tests/test_p2_features.py` | NOT_STARTED |
| FR-UI-05 | P1 | `backend/app/services/agents/copilot.py`, `api/v1/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_p2_features.py` | NOT_STARTED |
| FR-UI-06 | P1 | `backend/app/services/agents/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_p2_features.py` | NOT_STARTED |
| FR-UI-07 | P0 | `backend/app/services/agents/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_p2_features.py` | NOT_STARTED |
| FR-UI-08 | P1 | `backend/app/api/v1/reports.py` | `GET /api/v1/reports/export` | `backend/tests/test_p2_features.py` | NOT_STARTED |
| FR-AUD-01 | P0 | `backend/app/services/audit/service.py` | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-AUD-02 | P0 | `backend/app/models/audit.py` | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-AUD-03 | P0 | `backend/migrations/` (DB trigger) | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| FR-NOT-01 | P1 | `backend/app/services/notifications/` | `GET /api/v1/notifications` | `backend/tests/test_notifications.py` | NOT_STARTED |
| FR-NOT-02 | P0 | `backend/app/services/notifications/` | `GET /api/v1/notifications` | `backend/tests/test_notifications.py` | NOT_STARTED |

## Non-Functional Requirements (NFR)

| ID | Priority | Module | API Endpoint | Test File | Status |
|---|---|---|---|---|---|
| NFR-PERF-01 | P1 | `backend/app/main.py` | `GET /api/v1/dashboard/summary`, `/transactions` | `backend/tests/test_performance.py` | NOT_STARTED |
| NFR-PERF-02 | P0 | `backend/app/workers/job_worker.py` | `POST /api/v1/documents`, `GET /api/v1/jobs/{id}` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| NFR-REL-01 | P0 | `backend/app/workers/job_worker.py` | `POST /api/v1/documents` | `backend/tests/test_failure_injection.py` | NOT_STARTED |
| NFR-REL-02 | P0 | `backend/app/models/job.py`, `api/v1/admin.py` | `GET /api/v1/admin/jobs`, `POST /api/v1/admin/jobs/{id}/retry` | `backend/tests/test_failure_injection.py` | NOT_STARTED |
| NFR-SEC-01 | P0 | `backend/app/core/security.py` | `POST /api/v1/auth/login` | `backend/tests/test_auth_rbac.py` | IMPLEMENTED |
| NFR-SEC-02 | P0 | `.env.example`, `backend/app/core/config.py` | N/A | `backend/tests/test_security_sweep.py` | IMPLEMENTED |
| NFR-SEC-03 | P0 | `backend/app/repositories/base.py`, `core/permissions.py` | All `/api/v1/*` | `backend/tests/test_security_sweep.py` | IMPLEMENTED |
| NFR-AUD-01 | P0 | `backend/app/services/audit/service.py` | `GET /api/v1/audit` | `backend/tests/test_audit.py` | IMPLEMENTED |
| NFR-MAINT-01 | P0 | `backend/app/services/*` | N/A | `backend/tests/test_architecture_boundaries.py` | NOT_STARTED |
| NFR-TEST-01 | P0 | `backend/app/services/reconciliation/` | N/A | `backend/tests/test_reconciliation_engine.py` | IMPLEMENTED |
| NFR-SCALE-01 | P1 | `backend/app/workers/job_worker.py` | `POST /api/v1/documents` | `backend/tests/test_document_pipeline.py` | NOT_STARTED |
| NFR-UX-01 | P1 | `frontend/src/*` | N/A | `frontend/e2e/smoke.spec.ts` | NOT_STARTED |
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
| AT-07 | P0 | `services/documents/` | `GET /api/v1/documents/{id}`, `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_acceptance.py` | NOT_STARTED |
| AT-08 | P0 | `services/agents/` | `POST /api/v1/exceptions/{id}/investigations` | `backend/tests/test_acceptance.py` | NOT_STARTED |
| AT-09 | P0 | `api/v1/exceptions.py`, `core/permissions.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_acceptance.py` | NOT_STARTED |
| AT-10 | P0 | `services/graph/`, `services/reconciliation/` | `GET /api/v1/graph/transactions/{id}`, `POST /api/v1/transactions/{id}/reconcile` | `backend/tests/test_acceptance.py` | NOT_STARTED |
| AT-11 | P0 | `services/agents/copilot.py` | `POST /api/v1/copilot/query` | `backend/tests/test_acceptance.py` | NOT_STARTED |
| AT-12 | P0 | `services/workflows/approval.py` | `POST /api/v1/exceptions/{id}/decision` | `backend/tests/test_acceptance.py` | NOT_STARTED |
