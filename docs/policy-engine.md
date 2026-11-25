# ReconX AI — Dynamic Policy Engine & Re-Audit Guide

## 1. Architecture
- **Models (`backend/app/models/policy.py`, migration `0003_policies_and_briefs`):**
  - `Policy` — Logical policy identity, category, severity, lifecycle status (`DRAFT -> VALIDATED -> ACTIVE -> INACTIVE -> ARCHIVED`), `active_version_id`.
  - `PolicyVersion` — Immutable definition snapshot (`definition_json`), SHA-256 `content_hash`, `version_number`, `activated_at`.
  - `PolicyAuditRun` — Historical Re-Audit run summary (`transactions_scanned`, `new_exceptions`, `existing_exceptions`, `resolved_exceptions`).
  - `PolicyEvaluation` — Per-transaction evaluation outcome with `violation_fingerprint` for idempotency.

## 2. Constrained Rule DSL (`backend/app/services/policies/dsl.py`)
- **Zero `eval()` or arbitrary SQL/code execution.**
- Strict Pydantic validation (`extra="forbid"`, max nesting depth `3`, max conditions `15`, `Decimal` arithmetic).
- **Allowlisted Fields:** `purchase_order.*`, `goods_receipt.*`, `invoice.*`, `variance.qty_diff`, `variance.amount_diff`, `variance.price_diff_pct`, `vendor.*`.
- **Allowlisted Operators:** `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `exists`, `between` (`AND` / `OR` groups).

## 3. Live Hot-Swap & Re-Audit Workflow
1. Create or edit a policy in **Intelligence → Policy Studio** (`/policy-studio`).
2. Run **Preview Policy Impact (Dry-Run)** (`POST /api/v1/policies/preview`) without creating exceptions.
3. Click **Activate** (`POST /api/v1/policies/{id}/activate`) — creates an immutable `PolicyVersion` and takes effect immediately without restarting FastAPI.
4. Click **Re-Run Audit** (`POST /api/v1/policy-audits`) to scan historical transactions and highlight `Newly Flagged`, `Existing Violations`, and `No Longer Triggered`.
