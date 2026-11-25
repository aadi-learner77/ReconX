# ReconX AI — AI Agent Pipeline Test Report

## 1. Seven-Agent Orchestration (`FinanceOrchestrator`)
Verified live against `AT-02` (`PO-2026-0002`, `QTY_OVER_BILLED`):
1. `DocumentAgent` — Inspected linked documents & `NEEDS_REVIEW` flags.
2. `MatchingAgent` — Evaluated 3-way bundle completeness (PO, GRNs, Invoices).
3. `RiskAgent` — Evaluated duplicate, split-invoice, MAD price, shared bank, and IsolationForest signals.
4. `VendorIntelligenceAgent` — Loaded vendor profile (`tx_count`, `mismatch_rate`, `small_sample_warning`).
5. `EvidenceGraphAgent` — Traversed relational evidence graph (`11` nodes, `10` edges, historical POs).
6. `InvestigationAgent` — Synthesized summary via `GeminiLLMProvider` (`gemini-2.5-flash`) with `<<<UNTRUSTED_DOCUMENT_CONTENT>>>` fencing + `validate_evidence_refs()` (`5` DB-verified refs).
7. `AuditAgent` — Logged `AGENT_TOOL_*` events and persisted `DRAFT_READY` investigation (`human_approval_required=True`).

- **Measured Live Latency (`LLM_PROVIDER=gemini`):** `7,547.12 ms`
- **Grounding Rate (`run_evaluation.py`):** `100.0%` (`5/5` cases, `0` fabricated refs).
