# ReconX AI — Benchmark & Feasibility Report

Measured metrics below were recorded by executing `backend/scripts/run_evaluation.py` on `2026-11-25T18:24:29Z` against SQLite + `LLM_PROVIDER=mock` + PyMuPDF + RapidOCR + openpyxl on the synthetic corpus (`8` vendors, `40` POs, `42` invoices, `6` evaluation documents).

## 1. Measured ReconX AI Performance

| Metric | Measured Result | Sample / Denominator |
|---|---|---|
| **Extraction Key-Field Accuracy** | **86.96%** | `20 / 23` fields |
| **3-Way Reconciliation Decision Accuracy** | **100.00%** | `11 / 11` transactions |
| **Duplicate Detection Precision / Recall** | **100.0% / 100.0%** | `12` pairs (`6` TP, `0` FP, `0` FN) |
| **Anomaly ML Holdout (P / R / F1 / FPR)** | **1.00 / 1.00 / 1.00 / 0.00** | `20` held-out samples |
| **Investigation Evidence Grounding Rate** | **100.0%** | `5 / 5` cases |
| **Document Ingestion Latency (Median / P95)** | **228.53 ms / 13,085.59 ms** | `6` documents (P95 includes PNG OCR) |
| **Core Read API Latency (Median / P95)** | **52.39 ms / 68.80 ms** | `60` requests (`NFR-PERF-01` target `< 2000 ms`) |

## 2. Manual AP Reconciliation vs. ReconX AI (Reference Comparison)

> **Methodology Note:** Manual AP figures below are standard workflow reference estimates (not timed human-subject trials), contrasted against ReconX AI's **measured** automated timings above.

| Dimension | Typical Manual AP Workflow (Reference) | ReconX AI (Measured) |
|---|---|---|
| **3-Way Line-Level Check (PO + Multi-GRN + Invoice)** | Several minutes per bundle; prone to float/rounding drift | **Deterministic `Decimal` match** in milliseconds (`100%` accuracy on `11/11` scenarios) |
| **Document Parsing & OCR** | Manual key-entry from PDFs/scans/Excel | **228.53 ms median** (`86.96%` auto-extracted fields; low-confidence queued for human review) |
| **Exception Context Gathering** | Manual lookup across emails, ERP tabs, vendor history | **Single-click `FinanceOrchestrator`** (`DocumentAgent`, `MatchingAgent`, `RiskAgent`, `VendorIntelligenceAgent`, `EvidenceGraphAgent`, `InvestigationAgent`, `AuditAgent`) |
| **Audit & Governance** | Spreadsheet notes, mutable logs | **Append-only `audit_event`** with DB triggers + server-side RBAC + maker-checker |

## 3. Honest Limitations
- Evaluation corpus is synthetic (`seed=20260101`); real enterprise invoice layouts may require additional OCR/regex tuning.
- Live Gemini `:generateContent` fell back to deterministic `MockLLMProvider` (`explain: None`) with the provided key/model; fallback preserved 100% pipeline stability.
- Live Docker Compose + PostgreSQL (`OD-07`) was not executed on this host because Docker Desktop daemon is stopped.
