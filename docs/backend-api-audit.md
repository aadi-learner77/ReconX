# ReconX AI — Backend API Audit

All endpoints mounted under `/api/v1` (`backend/app/api/v1/router.py`):

- `health.py`: `GET /health` (`200 OK`, DB connectivity check)
- `auth.py`: `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`
- `documents.py`: `POST /documents` (`202`), `GET /documents`, `GET /documents/{id}`, `PATCH /documents/{id}/fields`, `POST /documents/{id}/verify`, `POST /documents/{id}/link`, `GET /jobs/{id}`
- `transactions.py`: `GET /transactions`, `GET /transactions/{id}`
- `reconciliation.py`: `POST /transactions/{id}/reconcile`
- `exceptions.py`: `GET /exceptions`, `GET /exceptions/{id}`, `POST /exceptions/{id}/assign`, `/comments`, `/decision`, `GET /notifications`, `POST /notifications/{id}/read`
- `vendors.py`: `GET /vendors`
- `intelligence.py`: `GET /transactions/{id}/risk`, `GET /vendors/{id}/profile`, `POST /vendors/{id}/bank-change`, `POST /exceptions/{id}/investigations`, `GET /investigations/{id}`, `GET /dashboard/summary`, `GET /graph/transactions/{id}`, `POST /graph/transactions/{id}/rebuild`, `POST /copilot/query`, `GET /analytics/cash-obligations`, `GET /reports/export`
- `audit.py`: `GET /audit`
- `admin.py`: `GET/PUT /admin/config`, `GET/PUT /admin/tolerances`, `GET/POST /admin/users`, `GET /admin/jobs`, `POST /admin/jobs/{id}/retry`

All routes enforce JWT + `require_permission(...)` + `OrgScopedRepository(organization_id)` tenant isolation.
