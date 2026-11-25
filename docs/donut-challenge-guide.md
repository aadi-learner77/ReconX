# ReconX AI — Donut Challenge Rapid Adaptation Guide

ReconX AI is designed so policy rules, tolerances, thresholds, and AI providers are **data-driven and configurable** rather than hardcoded. This guide documents how to adapt the system rapidly during a timed challenge without breaking deterministic financial guarantees.

---

## 1. Configurable Surfaces (Zero Code Change Required)

| Surface | Where Configured | How to Change Rapidly |
|---|---|---|
| **Price & Quantity Tolerances** | `tolerance_config` table (`GET/PUT /api/v1/admin/tolerances`) | Update `price_abs_tolerance`, `price_pct_tolerance`, `qty_abs_tolerance`, `qty_pct_tolerance`, or `tax_tolerance` per org or per vendor override. |
| **Approval Limits & Policy** | `app_config` table (`GET/PUT /api/v1/admin/config`) | Adjust role approval thresholds, confidence review thresholds, or service/advance policy toggles; all changes are versioned and audited. |
| **Feature Toggles** | `.env` (`FEATURE_EVIDENCE_GRAPH`, `FEATURE_FINANCE_COPILOT`, `FEATURE_ANOMALY_ML`, `FEATURE_CASH_VIEW`, `FEATURE_REPORT_EXPORTS`) | Enable/disable P2 subsystems cleanly without affecting core 3-way matching. |
| **AI Provider / Model** | `.env` (`LLM_PROVIDER`, `GEMINI_MODEL`, `GROQ_MODEL`, `OLLAMA_MODEL`) | Switch between `mock`, `gemini`, `groq`, and `ollama` via env var + backend restart. |
| **Upload Limits** | `.env` (`MAX_UPLOAD_SIZE_MB`) | Adjust allowed upload size without modifying code. |

---

## 2. Rapid Code Extension Points (If New Rules/Fields Are Introduced)

1. **New Document Type or Field Mapping**:
   - Extend `extractor.py` (`backend/app/services/documents/extractor.py`) regex/LLM schema fields and `ExtractionField` provenance keys; keep `verification_status` (`extracted` / `user_corrected` / `system_derived`).
2. **New Deterministic Reconciliation Rule**:
   - Add a pure `decimal.Decimal` rule function in `backend/app/services/reconciliation/rules.py` (no `float`, no DB/HTTP imports) and register its `rule_id` in `KNOWN_RULE_IDS` (`backend/app/services/agents/investigator.py`).
3. **New Vendor Validation / Risk Signal**:
   - Add a deterministic signal in `evaluate_transaction_risk` (`backend/app/services/risk/engine.py`) with `reason_codes`, `contributing_signals`, and the non-fraud `DISCLAIMER`.
4. **New Copilot Query Tool**:
   - Add a typed, `OrgScopedRepository`-backed `_tool_query_*` function in `backend/app/services/agents/copilot.py` (never raw SQL).

---

## 3. Rapid Verification Workflow (< 90 Seconds)

```powershell
# 1. Run deterministic math + API + security + gap-closure tests
cd backend
.\.venv\Scripts\pytest.exe tests/test_reconciliation_engine.py tests/test_srs_gap_closure.py tests/test_hardening_security.py -v

# 2. Static & boundary checks
.\.venv\Scripts\ruff.exe check app tests scripts
.\.venv\Scripts\mypy.exe app

# 3. Reset & re-seed demo dataset
cd ..
.\backend\.venv\Scripts\python.exe scripts\reset_demo.py
```
