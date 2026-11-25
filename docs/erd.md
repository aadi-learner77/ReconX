# Entity-Relationship Diagram — ReconX AI

Every business table uses UUID primary keys, `organization_id` tenant scoping, UTC timestamps, and `NUMERIC(18, 4)` for monetary amounts and quantities.

```mermaid
erDiagram
    ORGANIZATION ||--o{ USER : has
    ORGANIZATION ||--o{ VENDOR : owns
    ORGANIZATION ||--o{ PURCHASE_ORDER : scopes
    ORGANIZATION ||--o{ GOODS_RECEIPT : scopes
    ORGANIZATION ||--o{ INVOICE : scopes
    ORGANIZATION ||--o{ DOCUMENT : stores
    ORGANIZATION ||--o{ AUDIT_EVENT : logs
    ORGANIZATION ||--o{ APP_CONFIG : configures
    ORGANIZATION ||--o{ TOLERANCE_CONFIG : configures
    ORGANIZATION ||--o{ JOB : schedules

    USER ||--o{ USER_ROLE : assigned
    ROLE ||--o{ USER_ROLE : granted_to
    ROLE ||--o{ ROLE_PERMISSION : grants
    PERMISSION ||--o{ ROLE_PERMISSION : linked

    VENDOR ||--o{ PURCHASE_ORDER : receives
    VENDOR ||--o{ GOODS_RECEIPT : delivers
    VENDOR ||--o{ INVOICE : bills
    VENDOR ||--o{ TOLERANCE_CONFIG : overrides

    PURCHASE_ORDER ||--o{ PO_LINE : contains
    PURCHASE_ORDER ||--o{ GOODS_RECEIPT : receives_against
    PURCHASE_ORDER ||--o{ INVOICE : billed_against
    PURCHASE_ORDER ||--o{ RECONCILIATION_RUN : evaluated_by
    PURCHASE_ORDER ||--o{ EXCEPTION_CASE : triggers
    PURCHASE_ORDER ||--o{ RISK_SIGNAL : flagged_with

    PO_LINE ||--o{ GRN_LINE : fulfilled_by
    PO_LINE ||--o{ INVOICE_LINE : invoiced_by

    GOODS_RECEIPT ||--o{ GRN_LINE : contains
    INVOICE ||--o{ INVOICE_LINE : contains

    DOCUMENT ||--o{ EXTRACTION_FIELD : yields
    DOCUMENT ||--o{ PURCHASE_ORDER : source_of
    DOCUMENT ||--o{ GOODS_RECEIPT : source_of
    DOCUMENT ||--o{ INVOICE : source_of

    RECONCILIATION_RUN ||--o{ MATCH_RESULT : produces
    RECONCILIATION_RUN ||--o{ EXCEPTION_CASE : opens

    EXCEPTION_CASE ||--o{ INVESTIGATION : investigated_by
    EXCEPTION_CASE ||--o{ APPROVAL : decided_by
    USER ||--o{ APPROVAL : decides
    USER ||--o{ NOTIFICATION : receives
```

## Key Data Integrity Rules (SRS 8.3)
- **Unique invoice constraint**: `UNIQUE (organization_id, vendor_id, normalized_invoice_number)` on `invoice` (plus duplicate-handling metadata when an attempted duplicate is flagged for review).
- **Immutable audit trail**: PostgreSQL trigger raises an exception on `UPDATE` or `DELETE` on `audit_event`.
- **Money precision**: `NUMERIC(18, 4)` paired with explicit `currency` ISO-4217 column; zero float columns for currency or quantity.
- **Extraction provenance**: `extraction_field.verification_status` enum (`extracted`, `user_corrected`, `system_derived`) + `version` integer.
- **Optimistic locking**: `exception_case.version` integer prevents stale approval overwrites (`409 Conflict`).
