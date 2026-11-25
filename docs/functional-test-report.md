# ReconX AI — Functional Test Report

All core functional modules were verified via `pytest` (`40` backend tests), `vitest` (`3` frontend tests), Playwright E2E (`smoke.spec.ts` + `full_audit.spec.ts`), and live API rehearsal:

- **Authentication & RBAC (`FR-AUTH-01..05`):** Login, refresh, logout, invalid credentials (`401`), session persistence on reload, 6-role RBAC (`403` for operator on approval). **PASS.**
- **Document Centre (`FR-DOC-01..08`):** PDF, PNG (RapidOCR), XLSX (`openpyxl`), CSV, checksum dedup, magic-byte validation, unsupported/empty/oversized rejection, field correction & verification. **PASS.**
- **3-Way Reconciliation (`FR-MAT-01..09`, `AT-01..AT-06`):** Exact match, over-billing (`10 EA`), multi-GRN (`60+40`), price variance, duplicate invoice, missing PO/GRN, rejected goods, tax/currency/UOM mismatch, `Decimal` rounding. **PASS (`11/11`, `100%`).**
- **Exceptions & Approvals (`FR-EXC-01..09`, `FR-WF-01..06`, `AT-09`, `AT-12`):** Creation, assignment, comments, rationale-required decisions, maker-checker, optimistic locking (`409`). **PASS.**
- **Vendor Intelligence & Cash View (`FR-VEN-01..04`, `FR-UI-04`):** Profile metrics, small-sample warning (`N < 5`), due-date buckets + `forecast_30_60_90`. **PASS.**
- **Audit Trail (`FR-AUD-01..03`):** Login, upload, edit, reconcile, investigation, decision, graph rebuild, config change logged; DB triggers block `UPDATE`/`DELETE`. **PASS.**
