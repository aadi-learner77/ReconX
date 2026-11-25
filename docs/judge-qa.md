# ReconX AI — Judge Q&A Preparation Guide

## 1. Architecture & Determinism
**Q: Why use a single FastAPI + React + PostgreSQL architecture instead of microservices + Neo4j + Celery?**
- Matches Decision `D1`–`D9` and SRS 2.2 ("simplest viable architecture"): zero paid services, zero operational sprawl, and `15.8 ms` median API latency.
- Relational PostgreSQL/SQLite tables (`builder.py`) power the Financial Evidence Graph (`React Flow`) with `Investigation`, `RiskSignal`, `HistoricalPO`, and `DUPLICATE_OF` edges—so core reconciliation never fails if a graph service is down (`AT-10`).

**Q: How do you guarantee an LLM never corrupts financial totals or approves a payment?**
- `backend/app/services/reconciliation/` is a pure `decimal.Decimal` (`ROUND_HALF_UP`) package with **zero** `float`, SQLAlchemy, FastAPI, or LLM imports—enforced by AST tests in `test_hardening_security.py`.
- `ALLOWLISTED_AGENT_TOOLS` (`tools.py`) has **no** payment or approval tools, and `InvestigationOutputSchema` hardcodes `human_approval_required = True`.

## 2. AI Safety & Grounding
**Q: How do you prevent prompt injection from malicious supplier invoices (`AT-08`)?**
- All untrusted OCR/document text is fenced inside `<<<UNTRUSTED_DOCUMENT_CONTENT>>>` markers (`llm/adapter.py`) with system hygiene instructions.
- Even if an LLM were tricked, deterministic matching runs independently, and `validate_evidence_refs` (`investigator.py`) rejects any fabricated `rule_id` or non-existent UUID with HTTP `422 HALLUCINATED_EVIDENCE_REF`.

**Q: What happens if the external Gemini/Groq API key fails, rate-limits, or times out?**
- `_HTTPJsonLLMProvider` retries with backoff and falls back cleanly to deterministic extraction/classification/investigation templates—zero lost documents and zero broken workflows.

## 3. Fraud / Risk Indicators & ML
**Q: Does ReconX AI accuse vendors of fraud automatically?**
- Never. Every risk output (`risk/engine.py`) is explicitly labeled *"Risk indicator for human review, not proof of fraud."*
- Combines explainable deterministic rules (exact/near-duplicate invoices, `SPLIT_INVOICE_PATTERN`, `SHARED_BANK_ACCOUNT`, `ABNORMAL_INVOICE_FREQUENCY`, `BANK_DETAIL_CHANGE`, robust MAD z-score price spikes) with `IsolationForest` when `N >= 15` org invoices exist, falling back transparently with `limited_confidence` when data is thin.

## 4. Governance, Reliability & Deployment
**Q: How are RBAC, maker-checker, and audit immutability enforced?**
- Server-side `require_permission` RBAC across 6 roles (`operator` receives `403` on approval endpoints, `AT-09`).
- Maker-checker blocks self-approval; optimistic locking (`version`) prevents stale overwrites (`409 Conflict`).
- Database triggers on `audit_event` block `UPDATE` and `DELETE` at the DB level (`0001_foundation.py` + `ensure_sqlite_audit_triggers`).
