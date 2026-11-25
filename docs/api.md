# ReconX AI — REST API Reference (`/api/v1`)

Interactive OpenAPI / Swagger documentation is served at `GET /docs` and `GET /openapi.json` when the backend is running. Detailed request/response contracts are specified in [api-contracts.md](api-contracts.md).

## Conventions

- **Base Prefix**: `/api/v1`
- **Authentication**: `Authorization: Bearer <access_token>` (HS256 JWT via `POST /api/v1/auth/login`).
- **Tenant Scoping**: Every query is scoped strictly to `organization_id` from the verified JWT claims.
- **Correlation IDs**: Requests accept/emit `X-Correlation-ID` for end-to-end log and audit traceability.
- **Concurrency Control**: Approval decisions enforce optimistic locking via `version` and return `409 Conflict` on stale updates.
- **Role Model**: `finance_operator`, `approver`, `procurement`, `receiving`, `auditor`, `admin`.

## Endpoints

### Health & Authentication
| Method | Path | Purpose | Auth / Role |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service and database health check | Public |
| `POST` | `/api/v1/auth/login` | Issue access & refresh tokens (rate-limited) | Public |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token and issue new access token | Refresh Token |
| `POST` | `/api/v1/auth/logout` | Revoke active refresh token | Authenticated |
| `GET` | `/api/v1/auth/me` | Current user profile, org, roles, permissions | Authenticated |

### Documents & Ingestion Jobs
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/documents` | Upload PDF/PNG/JPG/XLSX/CSV (`multipart/form-data`), queues extraction job (`202`) |
| `GET` | `/api/v1/documents` | Paginated document list for current org |
| `GET` | `/api/v1/documents/{document_id}` | Document metadata, classification confidence, and extracted fields |
| `GET` | `/api/v1/documents/{document_id}/file` | Stream original immutable document bytes |
| `PATCH` | `/api/v1/documents/{document_id}/fields` | Correct extracted field values and record human verification edits |
| `POST` | `/api/v1/documents/{document_id}/link` | Link document to PO/GRN/Invoice |
| `POST` | `/api/v1/documents/{document_id}/verify` | Mark document verified after review |
| `GET` | `/api/v1/jobs/{job_id}` | Poll background extraction job status (`QUEUED`/`PROCESSING`/`SUCCEEDED`/`FAILED`) |

### Vendors, Transactions & Three-Way Matching
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/vendors` | List vendors in organization |
| `POST` | `/api/v1/vendors` | Create vendor |
| `GET` | `/api/v1/vendors/{vendor_id}` | Get vendor details |
| `GET` | `/api/v1/purchase-orders` | List purchase orders |
| `POST` | `/api/v1/purchase-orders` | Create purchase order with line items |
| `GET` | `/api/v1/goods-receipts` | List goods receipt notes |
| `POST` | `/api/v1/goods-receipts` | Create goods receipt note |
| `GET` | `/api/v1/invoices` | List invoices |
| `POST` | `/api/v1/invoices` | Create invoice |
| `GET` | `/api/v1/transactions` | Filterable transaction list (supplier, date, status, amount, risk) |
| `GET` | `/api/v1/transactions/{transaction_id}` | Full 3-way transaction bundle (PO + GRNs + Invoices + MatchResult) |
| `POST` | `/api/v1/transactions/{transaction_id}/reconcile` | Execute deterministic `Decimal` 3-way reconciliation engine |

### Exceptions, Workflow Approvals & Notifications
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/exceptions` | List reconciliation exception cases |
| `GET` | `/api/v1/exceptions/{case_id}` | Get exception details, rule breakdowns, comments, and approvals |
| `POST` | `/api/v1/exceptions/{case_id}/assign` | Assign exception case to reviewer |
| `POST` | `/api/v1/exceptions/{case_id}/comments` | Add review comment |
| `POST` | `/api/v1/exceptions/{case_id}/decision` | `APPROVE` / `REJECT` / `REQUEST_INFO` / `ESCALATE` (enforces RBAC, maker-checker, approval limits, rationale, optimistic lock) |
| `GET` | `/api/v1/notifications` | List in-app notifications for current user |
| `POST` | `/api/v1/notifications/{notification_id}/read` | Mark notification read |

### Intelligence, P2 Features & Audit
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/transactions/{transaction_id}/risk` | Deterministic risk indicators (non-fraud signals) |
| `GET` | `/api/v1/vendors/{vendor_id}/profile` | Vendor delivery/mismatch/billing history with explicit sample count `N` |
| `POST` | `/api/v1/vendors/{vendor_id}/bank-change` | Record bank-detail change alert requiring enhanced verification |
| `POST` | `/api/v1/exceptions/{case_id}/investigations` | Run guarded AI investigation with allowlisted read-only tools & grounded `evidence_ref` links |
| `GET` | `/api/v1/investigations/{investigation_id}` | Retrieve stored investigation findings |
| `GET` | `/api/v1/dashboard/summary` | Dashboard KPIs, queues, and outcome distribution |
| `GET` | `/api/v1/graph/transactions/{transaction_id}` | Financial Evidence Graph nodes & edges (feature-flagged `ENABLE_GRAPH` / `FEATURE_EVIDENCE_GRAPH`) |
| `POST` | `/api/v1/copilot/query` | Read-only Finance Copilot (no text-to-SQL, org/RBAC scoped) |
| `GET` | `/api/v1/analytics/cash-obligations` | Scheduled cash obligations & exposure analytics |
| `GET` | `/api/v1/reports/export` | Export reconciliation / audit summary (`csv` / `json`) |
| `GET` | `/api/v1/audit` | Query append-only immutable audit events |

### Administration
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/admin/users` | List organization users |
| `POST` | `/api/v1/admin/users` | Create user (`admin` only) |
| `PATCH` | `/api/v1/admin/users/{user_id}/roles` | Update user roles (`admin` only) |
| `GET` | `/api/v1/admin/config` | Get active `AppConfig` (approval limits, maker-checker threshold, LLM provider) |
| `PUT` | `/api/v1/admin/config` | Update versioned `AppConfig` (`admin` only) |
| `GET` | `/api/v1/admin/tolerances` | List tolerance rules (`GLOBAL`, `VENDOR`, `ITEM_CATEGORY`) |
| `POST` | `/api/v1/admin/tolerances` | Create or update tolerance rule (`admin` only) |
| `GET` | `/api/v1/admin/jobs` | List background jobs (`FAILED` filter supported) |
| `POST` | `/api/v1/admin/jobs/{job_id}/retry` | Retry failed job (`admin` only) |
