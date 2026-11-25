# ReconX AI — Performance & Reliability Report

All metrics measured via `backend/scripts/run_evaluation.py` and live rehearsal:

| Metric | Measured Result | Notes |
|---|---|---|
| **Core Read APIs (Median / P95)** | **52.39 ms / 68.80 ms** | `60` requests (`NFR-PERF-01` target `< 2000 ms`) |
| **Document Upload + OCR/Extract (Median / P95)** | **228.53 ms / 13,085.59 ms** | `6` docs (PyMuPDF + RapidOCR PNG + openpyxl) |
| **7-Agent Live Investigation (Gemini `2.5-flash`)** | **7,547.12 ms** | Full 7-agent DAG + DB evidence validation |
| **3-Way Reconciliation Accuracy** | **100.00%** | `11/11` scenarios |
| **Duplicate Rule Precision / Recall** | **100.0% / 100.0%** | `12` pairs |
| **Anomaly ML Holdout (P / R / F1 / FPR)** | **1.00 / 1.00 / 1.00 / 0.00** | `20` held-out samples |

## Reliability
- Background `Job` table supports `QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED` states, idempotency keys, bounded retries (`JOB_MAX_ATTEMPTS=3`), and admin retry endpoint.
- Optimistic locking (`version`) prevents concurrent approval overwrites (`409 Conflict`).
