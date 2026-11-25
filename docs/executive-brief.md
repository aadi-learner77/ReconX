# ReconX AI — Executive Boardroom Brief Engine

## 1. Purpose
Generates an immutable, reproducible, evidence-cited CFO/auditor report (`POST /api/v1/executive-briefs`) from authoritative database records.

## 2. Deterministic Calculations & Citations
- **Metrics:** Aggregated from `Document`, `PurchaseOrder`, `ReconciliationRun`, and `ExceptionCase` scoped strictly to `current_user.organization_id`.
- **Financial Exposure (`Decimal`):** Line-level quantity/price variance deduplicated per transaction to prevent double-counting.
- **Top 3 Urgent Exceptions:** Ranked deterministically by `Severity (CRITICAL > HIGH > MEDIUM > LOW)` → `Exposure` → `Oldest Created At` → `ID`.
- **Verified Citations (`CIT-001`..):** Every finding links directly to persisted `PurchaseOrder`, `GoodsReceipt`, `Invoice`, and `ExceptionCase` records.
- **Exports (`GET /api/v1/executive-briefs/{id}/download?format=pdf|markdown|csv`):** ReportLab multi-page PDF, structured Markdown, and formula-injection-safe CSV, all audited via `EXECUTIVE_BRIEF_GENERATED` and `EXECUTIVE_BRIEF_DOWNLOADED`.
