# ReconX AI — Measured Evaluation Report

Generated automatically by `backend/scripts/run_evaluation.py` at `2026-11-25T18:24:29.601901+00:00` on
SQLite + `LLM_PROVIDER=mock` + PyMuPDF/RapidOCR + openpyxl (synthetic evaluation corpus only).

## 1. Environment & Corpus Summary
- Environment: Windows + Python 3.13 + SQLite + `LLM_PROVIDER=mock` + PyMuPDF + RapidOCR + openpyxl.
- Fixed Seeds: `random.Random(20260101)` (DB seed), `random.Random(2026)` & `random_state=42` (ML).
- Seeded Corpus: **8** vendors, **40** POs,
  **42** invoices; **6** fresh docs.
- IsolationForest Split: **88** train (80 normal + 8 outliers) / **20** held-out test (12 + 8).

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
| Document Upload + OCR/Extract Job | **228.53 ms** | **13085.59 ms** | PyMuPDF + RapidOCR PNG + openpyxl |
| Core Read APIs (in-process TestClient) | **52.39 ms** | **68.8 ms** | NFR-PERF-01 < 2000 ms P95 (60 reqs) |
| Concurrent External Load (`locust` / `k6`) | not measured | not measured | Tool not installed |

## 4. Security & Static Tooling Snapshot
- `ruff check`, `mypy app`, `eslint`, and AST/regex secret scan pass (`0` issues).
- `npm audit --omit=dev --audit-level=high`: `0` high/critical production advisories.
- `gitleaks` & `pip-audit`: CLI binaries not installed on host (secret scan runs via pytest).

## 5. Honest Limitations
- Evaluation ran against deterministic synthetic fixtures (`LLM_PROVIDER=mock`) on local Windows
  SQLite rather than live external Gemini/Groq APIs or live Docker PostgreSQL (see `OD-07` in
  `docs/DECISIONS.md`).
- IsolationForest metrics reflect a clean synthetic split rather than real AP distributions.
