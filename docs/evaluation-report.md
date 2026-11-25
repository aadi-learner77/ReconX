# ReconX AI — Measured Evaluation Report

Generated automatically by `backend/scripts/run_evaluation.py` at `2026-11-25T16:18:31.083372+00:00` on
SQLite + `LLM_PROVIDER=mock` + PyMuPDF/RapidOCR + openpyxl (synthetic evaluation corpus only).

## 1. Corpus Summary
- Seeded Vendors: **8**
- Seeded Purchase Orders: **40**
- Seeded Invoices: **42**
- Fresh Extraction Benchmark Documents: **6**

## 2. Measured Quality & Safety Metrics

| Metric | Measured Value | Denominator / Sample | Target / SLA |
|---|---|---|---|
| Extraction Key-Field Accuracy | **86.96%** | 20/23 fields | Track exact vs ground truth |
| Reconciliation Decision Accuracy | **100.00%** | 11/11 txns | 100% deterministic parity |
| Duplicate Rule Precision / Recall | **100.0% / 100.0%** | 12 pairs | Zero missed duplicates |
| Anomaly ML Holdout (P / R / F1 / FPR) | **1.00 / 1.00 / 1.00 / 0.00** | 20 samples | Indicator |
| Investigation Evidence Grounding Rate | **100.0%** | 5/5 cases | 100% DB-resolvable refs |

## 3. Measured Latency Metrics

| Workload | Median | P95 | Notes |
|---|---|---|---|
| Document Upload + OCR/Extract Job | **131.66 ms** | **5426.12 ms** | PyMuPDF + RapidOCR PNG + openpyxl |
| Core Read APIs | **38.18 ms** | **53.92 ms** | NFR-PERF-01 < 2000 ms P95 (60 reqs) |

## 4. Honest Limitations
- Evaluation ran against deterministic synthetic fixtures (`LLM_PROVIDER=mock`) on local Windows
  SQLite rather than live external Gemini/Groq APIs or live Docker PostgreSQL (see `OD-07` in
  `docs/DECISIONS.md`).
- IsolationForest metrics reflect a clean synthetic split rather than real AP distributions.
