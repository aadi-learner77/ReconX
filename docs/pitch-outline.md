# ReconX AI — Hackathon Pitch Outline (Synchronise 2026, PS-BA1)

1. **The AP Bottleneck**: Mid-market finance teams reconcile POs, GRNs, and Vendor Invoices across mixed PDFs, scans, and spreadsheets manually — missing duplicate invoices, price creep, and short deliveries while risking AI hallucination or prompt injection if handed straight to an LLM.
2. **Core Thesis — Deterministic Money, AI-Assisted Evidence**:
   - **Pure Python `Decimal` Engine**: 13 rule checks (`R-PO-01`..`R-LINK-01`), zero floats, zero DB/LLM coupling inside matching, 96%+ tested coverage + Hypothesis properties.
   - **Fail-Closed Ingestion & Verification**: PyMuPDF + RapidOCR + openpyxl with magic-byte validation, SHA-256 deduplication, confidence gating (`REVIEW_REQUIRED`), and DB-backed retries.
   - **Explainable Risk Indicators + Grounded Copilot**: Near-duplicate fuzzy matching, MAD z-score price spikes, bank-change verification holds, IsolationForest outlier indicators (`non-fraud disclaimer`), and post-validated evidence links (`HALLUCINATED_EVIDENCE_REF` rejection).
3. **Security & Governance by Construction**:
   - Untrusted text isolation, allowlisted read/draft agent tools only, maker-checker RBAC, approval amount tiers, optimistic locking, and DB-trigger-enforced append-only `audit_event`.
4. **100% Free, Zero-Lock-In Architecture**:
   - Single FastAPI + React/TS + PostgreSQL stack (`LLM_PROVIDER=mock|gemini|groq|ollama`), Docker Compose ready, cloud-portable free-tier guide.
5. **Measured Proof (`docs/evaluation-report.md`)**:
   - Automated Playwright E2E + backend pytest + Vitest + benchmarked extraction, reconciliation parity, duplicate P/R, agent grounding, and < 2s P95 API reads.
