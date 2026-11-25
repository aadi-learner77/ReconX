# ReconX AI — Hackathon Viva & Judge Q&A Preparation (100+ Questions)

> **How to use:** Each question has a **Direct Answer** + **ReconX Code/Evidence Link**.

---

## 1. Business & Problem Statement (Q1–Q10)
1. **What problem does ReconX solve?** Automates 3-way PO ↔ GRN ↔ Invoice matching to prevent over-billing, duplicate payments, and manual spreadsheet errors.
2. **Who is the target user?** Finance Operators, Approvers, Procurement, Receiving, Auditors, and Admins.
3. **Why is 3-way matching better than 2-way matching?** 2-way only checks PO vs Invoice; 3-way checks the warehouse GRN to prove goods actually arrived.
4. **What happens if a company pays before checking GRNs?** It pays for short-shipped or rejected goods (`AT-02`: 10 missing bolts = ₹1,200 loss).
5. **Can ReconX handle partial deliveries?** Yes (`AT-03`: `PO-2026-0003` aggregates `GRN-2026-0003A` (60) + `GRN-2026-0003B` (40) = 100 without double-counting).
6. **Does ReconX execute bank transfers?** No. It is a reconciliation & authorization-workflow platform; payment execution is intentionally out of scope for safety.
7. **What industries need this?** Manufacturing, retail, construction, healthcare—any business with physical POs and GRNs.
8. **What is the ROI?** Faster exception triage, zero duplicate-invoice leakage, and instant audit readiness.
9. **Does it replace an ERP?** No, it sits alongside ERPs (or ingests exported PO/GRN/Invoice PDFs, Excel, CSVs).
10. **What if a supplier sends a scanned image instead of a digital PDF?** RapidOCR extracts text and queues low-confidence fields for human review (`AT-07`).

## 2. Financial Reconciliation (Q11–Q22)
11. **Why use `decimal.Decimal` instead of `float`?** Binary floats cause rounding drift (`0.1 + 0.2 != 0.3`); `Decimal` + `NUMERIC(18,4)` guarantees exact cent/paisa math (`services/reconciliation/money.py`).
12. **How are tolerances applied?** Configurable per org/vendor/item in `ToleranceConfig` (e.g., 2% price tolerance, 0% qty over-billing).
13. **What outcomes can reconciliation produce?** `MATCHED`, `MATCHED_WITH_TOLERANCE`, `EXCEPTION`, `INCOMPLETE`, `REVIEW_REQUIRED`.
14. **How do you handle rejected goods?** `accepted_qty` is summed separately from `rejected_qty` (`quantities.py`); only accepted units are eligible for billing.
15. **What if an invoice has no PO?** Marked `INCOMPLETE` and raises a missing-PO exception (`AT-06`).
16. **How do you detect duplicate invoices?** Exact normalized invoice number constraint + fuzzy near-duplicate check (`R-DUP-01`).
17. **What if currency differs between PO and Invoice?** Flagged by `R-CUR-01`.
18. **What if unit of measure (UOM) differs?** Flagged by `R-UOM-01` (e.g., `EA` vs `BOX`).
19. **How is tax checked?** `R-TAX-01` compares invoice tax against expected PO/line tax within `tax_abs_tolerance`.
20. **Is reconciliation idempotent?** Yes; re-running replaces open auto-generated exceptions cleanly without duplicating them.
21. **Can an LLM override a failed rule?** Never (`FR-MAT-09`).
22. **How do you test financial math?** Unit tests + Hypothesis property-based tests in `test_reconciliation_engine.py`.

## 3. Technical Architecture (Q23–Q34)
23. **Why FastAPI + React + PostgreSQL?** Simplest viable, 100% free-tier stack—single backend, single frontend, single DB (no microservices sprawl).
24. **Why no Redis/Celery?** Decision `D1`: a DB-backed `jobs` table + in-process worker thread handles async OCR jobs with zero extra infrastructure.
25. **Why no Neo4j?** Decision `D2`: PostgreSQL relational edge queries + React Flow deliver both Evidence & Obligation graphs without syncing a second database (`AT-10`).
26. **How does the frontend talk to the backend?** Typed `fetch` wrapper in `frontend/src/api/client.ts` with JWT Bearer headers and TanStack React Query.
27. **How are schema changes managed?** Reversible Alembic migrations (`0001_foundation` through `0004_llm_telemetry`).
28. **Does it work on both PostgreSQL and SQLite?** Yes; PostgreSQL 16 runs in Docker Compose, SQLite runs for fast local tests.
29. **How are files stored?** Local disk behind `StorageAdapter` using random UUID keys and SHA-256 checksums (`services/documents/storage.py`).
30. **How do you prevent duplicate file uploads?** Cryptographic SHA-256 checksum check (`FR-DOC-04`).
31. **How is logging structured?** JSON logs with `X-Correlation-ID` and `X-Request-ID` middleware (`main.py`, `core/logging.py`).
32. **What PDF library do you use?** PyMuPDF (`fitz`) for reading PDFs, ReportLab for generating Executive Brief PDFs.
33. **How do you handle CORS?** Configured via `CORS_ORIGINS` env var in `config.py`.
34. **Is Docker verified?** Yes—Docker `29.9.3` / Compose `v5.7.1` with `postgres:16-alpine` verified live (`docs/docker-postgresql-verification.md`).

## 4. AI & Google Gemini (Q35–Q48)
35. **Which exact operations use Google Gemini?** `InvestigationAgent` (`LLMProvider.explain` in `investigator.py`) and optional `classify`/`extract` in `adapter.py`.
36. **Which Gemini model is configured?** `gemini-2.5-flash` via `GEMINI_MODEL` (verified live on `generateContent`).
37. **Why did you also keep `mock`, `groq`, and `ollama`?** Offline reliability, zero-cost automated tests (`mock`), and provider portability (`D3`).
38. **How do you prevent Gemini from hallucinating evidence?** `validate_evidence_refs()` checks every cited UUID against `OrgScopedRepository` and rejects unknown IDs with HTTP `422`.
39. **What happens if Gemini times out or hits a 429 rate limit?** `_HTTPJsonLLMProvider` retries once, categorizes the error (`TIMEOUT`, `RATE_LIMITED`), falls back to `mock`, and records `fallback_used=True`.
40. **How do judges know an output really came from Gemini?** Investigation & trace cards display `"Generated with Google Gemini"` ONLY when `actual_provider == "gemini" && !fallback_used`; otherwise `"Mock fallback used — not Gemini-generated."`.
41. **Is the Gemini API key ever sent to the frontend?** Never. It stays strictly in backend `.env` (`config.py`) and is excluded from telemetry & API responses.
42. **How do you measure Gemini performance?** `llm_telemetry` table records real latency (`ms`), success/failure, and fallback counts.
43. **Why show Token Usage as Unavailable?** Because `_complete_json` extracts the text candidate without fabricating token counts (`NFR` honesty rule).
44. **What is `SYSTEM_PROMPT_HYGIENE`?** Instructions telling Gemini to treat `<<<UNTRUSTED_DOCUMENT_CONTENT>>>` strictly as inert evidence, ignoring embedded commands.
45. **Can Gemini approve an invoice?** No—it has no approval tool and `human_approval_required=True` is hardcoded.
46. **What does the "Test Gemini Connection" button do?** Admin-only `POST /api/v1/intelligence/gemini/test` sends a minimal JSON ping and logs `connection_test` telemetry without creating an investigation.
47. **Why `temperature: 0.0`?** Minimizes randomness for consistent JSON summaries.
48. **How is Gemini tested in CI without a live key?** `backend/tests/test_gemini_observability.py` mocks `httpx.Client` to test 200, 401, 404, 429, timeout, invalid JSON, and missing key.

## 5. Machine Learning & Risk Intelligence (Q49–Q58)
49. **What ML model is used?** `scikit-learn` `IsolationForest` on invoice total, tax, and line count (`services/risk/engine.py`).
50. **What if there aren't enough invoices for ML?** Falls back to deterministic rules when `N < 15`, and flags `limited_confidence=True` when `N < 30`.
51. **What deterministic risk signals exist?** `EXACT_DUPLICATE_INVOICE`, `NEAR_DUPLICATE_INVOICE`, `HISTORICAL_PRICE_DEVIATION` (MAD z-score), `SPLIT_INVOICE_PATTERN`, `ABNORMAL_INVOICE_FREQUENCY`, `SHARED_BANK_ACCOUNT`, `BANK_DETAIL_CHANGE`.
52. **Why MAD z-score instead of standard deviation?** Median Absolute Deviation is robust against extreme outliers in small vendor histories.
53. **Does ReconX accuse vendors of fraud?** Never. All outputs carry `"Risk indicator for human review, not proof of fraud."`.
54. **How is vendor reliability guarded?** Small-sample guard (`N < 5`) omits definitive scores and displays a warning (`FR-VEN-04`).
55. **How is split-invoice detection implemented?** Flags `>= 2` invoices against the same PO within ±7 days summing `>= 90%` of PO total.
56. **How is relationship anomaly detection implemented?** `SHARED_BANK_ACCOUNT` detects distinct vendors in the same org sharing `bank_account_masked`.
57. **How is predictive cash-flow forecasting implemented?** `GET /analytics/cash-obligations` combines scheduled due-date buckets with historical daily run-rate (`forecast_30_60_90`).
58. **What were the measured ML holdout metrics?** `P=1.00, R=1.00, F1=1.00, FPR=0.00` on 20 synthetic holdout samples (`docs/evaluation-report.md`).

## 6. Agent Harness & Copilot (Q59–Q68)
59. **Why build a Python DAG orchestrator instead of LangGraph?** Decision `D10`: zero extra dependency bloat, deterministic stage order, and per-stage `execution_trace` without extra LLM round-trips.
60. **What are the 7 stages in order?** `DocumentAgent` → `MatchingAgent` → `RiskAgent` → `VendorIntelligenceAgent` → `EvidenceGraphAgent` → `InvestigationAgent` → `AuditAgent`.
61. **Is the Agent Harness an 8th agent?** No, it is the governance & execution layer around the 7 agents.
62. **What is in `execution_trace`?** Agent name, `SUCCEEDED`/`FAILED` status, `duration_ms`, and stage summary.
63. **What happens if one agent fails?** `FinanceOrchestrator._run_node` records `FAILED` in `execution_trace` and aborts safely without creating a partial approval.
64. **How does Finance Copilot work?** Structured intent router calling typed, org-scoped SQLAlchemy queries (`services/agents/copilot.py`)—zero raw SQL.
65. **What if someone asks Copilot to "approve PO-2026-0001"?** Blocked by `WRITE_VERBS` guardrail, logged as `COPILOT_WRITE_BLOCKED`, returns `read_only=True`.
66. **Can Copilot leak another organization's data?** No (`AT-11`): every query uses `OrgScopedRepository(db, ..., org_id)`.
67. **What are the 8 Harness Infrastructure components?** Orchestrator, Shared Context Manager, Tool Registry, Permission & Policy Layer, LLM Provider Adapter, Evidence Validator, Execution Tracer, Human Approval Gate.
68. **Where can judges see the harness?** `/agent-harness` (`AgentHarnessPage.tsx`).

## 7. Policy Engine & Re-Audit (Q69–Q80)
69. **How does Zero-Code Policy Hot-Swap work?** Policies are stored as validated JSON in `policy` + `policy_version` tables and read live from DB on every reconciliation/audit.
70. **Why a constrained DSL instead of Python `eval()`?** `eval()` is a remote code execution vulnerability; our Pydantic DSL (`dsl.py`) only allows whitelisted fields and operators.
71. **How are policy versions kept immutable?** Editing an active/activated policy creates a new `PolicyVersion` row (`version_number + 1`) with a new SHA-256 `content_hash`.
72. **What is "Preview Policy Impact"?** A dry-run (`POST /policies/preview`) that evaluates draft conditions against org POs without creating exceptions.
73. **How does Re-Run Audit avoid duplicate exceptions?** `_create_or_reuse_exception` checks for existing `OPEN`/`IN_REVIEW`/`ESCALATED` cases with the same `(transaction_id, rule_id)` and tracks `violation_fingerprint`.
74. **What are the 3 lists in Re-Audit results?** `Newly Flagged`, `Existing Violations`, and `No Longer Triggered`.
75. **Can an Operator create or activate a policy?** No (`403 Forbidden`); requires `policies:create` / `policies:activate` (Admin only).
76. **Can system policies be deactivated?** No (`POL-SYS-DUP` is `is_system_policy=True`, returning `409 SYSTEM_POLICY_PROTECTED`).
77. **Does dynamic policy evaluation replace `R-QTY-01`?** No; it runs *after* built-in deterministic rules in `reconciliation_adapter.py`.
78. **What happens if a policy JSON has an unknown field?** Pydantic `extra="forbid"` + `ALLOWED_FIELDS` check rejects it with `422`.
79. **How is nested logic handled?** `ConditionGroup` supports `AND`/`OR` up to `MAX_NESTING_DEPTH=3` and `MAX_CONDITIONS=15`.
80. **Where is Policy Studio in the UI?** `Intelligence → Policy Studio` (`/policy-studio`).

## 8. Executive Brief & Obligation Graph (Q81–Q90)
81. **How is financial exposure calculated without double-counting?** `_calc_case_exposure` + `seen_tx_exposure` keeps the max verified line-level exposure per transaction.
82. **How are the Top 3 Urgent Exceptions ranked?** Deterministic sort: `Severity (CRITICAL > HIGH > MEDIUM > LOW)` → `Exposure` → `Oldest created_at` → `ID`.
83. **How do you prove citations aren't fabricated?** Every `CIT-*` citation is built directly from queried `PurchaseOrder`, `GoodsReceipt`, `Invoice`, and `ExceptionCase` rows in `executive_brief.py`.
84. **What export formats are supported?** Multi-page ReportLab PDF, Markdown (`.md`), and formula-injection-safe CSV (`.csv`).
85. **How do you prevent CSV formula injection?** `_csv_safe()` prefixes values starting with `=`, `+`, `-`, `@`, `\t`, `\r` with `'`.
86. **Are generated briefs reproducible?** Yes; `ExecutiveBrief` persists `metrics_json`, `exposure_json`, `top_exceptions_json`, `citations_json`, and `content_checksum`.
87. **What is the difference between Evidence View and Obligation View?** Evidence View shows provenance & investigation links (`RiskSignal`, `HistoricalPO`); Obligation View shows commitments (`POLine` -> `DeliveryObligation` <- `GRNLine` / `InvoiceLine`).
88. **Does Obligation Graph show fake "Settled Payment" edges?** Never (`has_payment_records: false`); settlement edges only appear if payment records exist.
89. **How is outstanding delivery quantity calculated?** `ordered_qty - accepted_qty` in `Decimal` on the backend (`builder.py`).
90. **What if an Executive Brief has fewer than 3 open exceptions?** It displays the actual count and explicitly notes this in `limitations`.

## 9. Security, Governance & Feasibility (Q91–Q102)
91. **How are passwords stored?** Argon2id hashing via `argon2-cffi` (`core/security.py`).
92. **How is tenant isolation enforced?** Every query goes through `OrgScopedRepository(db, model, organization_id)` using the JWT `org_id` claim.
93. **What is maker-checker?** The user who created/raised an exception cannot approve it (`services/workflows/approval.py`).
94. **Can an admin delete audit logs?** No; PostgreSQL & SQLite DB triggers raise an exception on `UPDATE` or `DELETE` on `audit_event`.
95. **How do you prevent prompt injection (`AT-08`)?** Document text is wrapped in `<<<UNTRUSTED_DOCUMENT_CONTENT>>>`, matching runs deterministically, and `tools.py` has no payment/approval tools.
96. **How do you prevent path traversal on file uploads?** Files are saved under random UUID `storage_key`s, never user-supplied filenames.
97. **What happens on concurrent exception approvals?** Optimistic locking (`version` column) returns `409 Conflict` to the stale request.
98. **Can this run 100% free in production?** Yes: Vercel/Netlify (frontend), Render free web service (backend), Neon/Supabase free Postgres, and `mock` or free-tier Gemini.
99. **What is the measured API latency?** `52.39 ms` median / `68.80 ms` P95 across 60 core read requests (`run_evaluation.py`).
100. **What is still partial/pending?** Human stopwatch measurements in `docs/benchmark-data-template.csv` (`BENCH-01..20`) are left blank until a timed human trial is conducted.
101. **How many automated tests pass?** `47` backend `pytest` tests, `3` frontend `vitest` tests, `2` Playwright E2E suites (`full_audit.spec.ts` + `smoke.spec.ts`), `0` Ruff/Mypy/ESLint errors.
102. **What is your one-sentence closing pitch?** *"ReconX AI combines 100% deterministic `Decimal` three-way matching and zero-code policy hot-swapping with Google Gemini-assisted, citation-verified investigations—giving finance teams speed without ever surrendering financial control."*
