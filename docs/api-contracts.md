# API Contracts — ReconX AI (`/api/v1`)

All protected routes require `Authorization: Bearer <access_token>` and server-side RBAC (`require_permission(code)`) plus `organization_id` tenant scoping.
All error responses conform to Appendix B.6:
```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human readable message",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

## Health & Auth
| Method | Path | Auth / Permission | Purpose |
|---|---|---|---|
| GET | `/api/v1/health` | Public | Liveness + DB connectivity check |
| POST | `/api/v1/auth/login` | Public (rate-limited) | Issue JWT access + refresh tokens; log `audit_event` |
| POST | `/api/v1/auth/refresh` | Refresh token | Rotate access token |
| POST | `/api/v1/auth/logout` | Authenticated | Revoke refresh token; log `audit_event` |
| GET | `/api/v1/auth/me` | Authenticated | Current user profile, org, roles, permissions |

## Admin & Configuration
| Method | Path | Permission | Purpose |
|---|---|---|---|
| POST | `/api/v1/admin/users` | `admin:users:write` | Register user & assign roles (admin-only registration) |
| GET | `/api/v1/admin/users` | `admin:users:read` | List users in organization |
| PATCH | `/api/v1/admin/users/{user_id}/roles` | `admin:users:write` | Update user roles |
| GET | `/api/v1/admin/config` | `admin:config:read` | Get active versioned app/workflow configuration |
| PUT | `/api/v1/admin/config` | `admin:config:write` | Update versioned config + audit before/after |
| GET | `/api/v1/admin/tolerances` | `admin:config:read` | List tolerance configs (org + vendor/item overrides) |
| POST/PUT | `/api/v1/admin/tolerances` | `admin:config:write` | Create/update tolerance rule + audit |
| GET | `/api/v1/admin/jobs` | `admin:jobs:read` | List background jobs (filter by `FAILED`, etc.) |
| POST | `/api/v1/admin/jobs/{job_id}/retry` | `admin:jobs:write` | Re-queue failed job within retry controls |

## Core Records & Transactions
| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET/POST | `/api/v1/vendors` | `vendors:read` / `vendors:write` | List/create vendors |
| GET | `/api/v1/vendors/{vendor_id}/profile` | `vendors:read` | Vendor metrics, date range, N, price trends, disputes |
| POST | `/api/v1/vendors/{vendor_id}/bank-change` | `vendors:write` | Record bank-detail change event -> enhanced verification |
| GET/POST | `/api/v1/purchase-orders` | `transactions:read` / `transactions:write` | List/create POs with lines |
| GET/POST | `/api/v1/goods-receipts` | `transactions:read` / `receiving:write` | List/create GRNs with lines |
| GET/POST | `/api/v1/invoices` | `transactions:read` / `transactions:write` | List/create invoices with lines |
| GET | `/api/v1/transactions` | `transactions:read` | Paginated, filtered PO-centric transactions list |
| GET | `/api/v1/transactions/{transaction_id}` | `transactions:read` | Full bundle: PO, lines, GRNs, invoices, latest run, exceptions |
| POST | `/api/v1/transactions/{transaction_id}/reconcile` | `reconciliation:run` | Run deterministic 3-way matching engine; return Appendix B.3 |
| GET | `/api/v1/transactions/{transaction_id}/risk` | `transactions:read` | Explainable risk indicators & reason codes |

## Documents & Extraction
| Method | Path | Permission | Purpose |
|---|---|---|---|
| POST | `/api/v1/documents` | `documents:write` | Multipart upload; returns `{document_id, status: "QUEUED", job_id}` |
| GET | `/api/v1/documents` | `documents:read` | List uploaded documents |
| GET | `/api/v1/documents/{document_id}` | `documents:read` | Document metadata, status, extracted fields with provenance |
| GET | `/api/v1/documents/{document_id}/file` | `documents:read` | Serve original file bytes (authorized only, never public path) |
| PATCH | `/api/v1/documents/{document_id}/fields` | `documents:write` | User-correct extracted fields (creates new version + audit) |
| POST | `/api/v1/documents/{document_id}/verify` | `documents:write` | Commit verified fields to structured PO/GRN/Invoice |
| POST | `/api/v1/documents/{document_id}/link` | `documents:write` | Confirm/override candidate PO link |
| GET | `/api/v1/jobs/{job_id}` | `documents:read` | Poll async job state |

## Exceptions, Investigations, Workflows & Audit
| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/api/v1/exceptions` | `exceptions:read` | List/filter exception cases |
| GET | `/api/v1/exceptions/{case_id}` | `exceptions:read` | Exception details, match results, comments, approvals |
| POST | `/api/v1/exceptions/{case_id}/assign` | `exceptions:manage` | Assign case owner |
| POST | `/api/v1/exceptions/{case_id}/comments` | `exceptions:comment` | Add case comment |
| POST | `/api/v1/exceptions/{case_id}/decision` | `approvals:decide` (or `exceptions:manage` for non-final info/escalate) | `APPROVE`, `REJECT`, `REQUEST_INFO`, `ESCALATE` with server checks |
| POST | `/api/v1/exceptions/{case_id}/investigations` | `investigations:run` | Trigger bounded investigation agent (Appendix B.4) |
| GET | `/api/v1/investigations/{investigation_id}` | `exceptions:read` | Structured investigation output with evidence refs |
| GET | `/api/v1/audit` | `audit:read` | Paginated, filtered append-only audit log |
| GET | `/api/v1/notifications` | Authenticated (self-scoped) | List in-app notifications (redacted sensitive fields) |
| POST | `/api/v1/notifications/{id}/read` | Authenticated (self-scoped) | Mark notification read |

## Dashboard & P2 Differentiators (Feature-Flagged)
| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | `transactions:read` | KPI counts, queues, recent activity, outcome breakdown |
| GET | `/api/v1/graph/transactions/{transaction_id}` | `transactions:read` | Relational Financial Evidence Graph nodes & edges |
| POST | `/api/v1/copilot/query` | `copilot:read` | Read-only natural-language query over authorized views |
| GET | `/api/v1/analytics/cash-obligations` | `transactions:read` | Due-date buckets & vendor obligation totals |
| GET | `/api/v1/reports/export` | `reports:export` | CSV / PDF export of filtered transactions/exceptions |
