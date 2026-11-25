# ReconX AI — Agent Architecture

ReconX AI uses a **deterministic Python DAG orchestrator** (`FinanceOrchestrator` in `backend/app/services/agents/orchestrator.py`) instead of an unconstrained autonomous loop (Decision `D10`). Every agent step operates through an **allowlisted, tenant-scoped, audited `AgentToolbox`** (`backend/app/services/agents/tools.py`).

## 1. Multi-Agent Investigation Pipeline (`POST /api/v1/exceptions/{id}/investigations`)

```mermaid
flowchart TD
    START["ExceptionCase + CurrentUserContext"] --> ORCH["FinanceOrchestrator.run_pipeline()"]
    ORCH --> DOC["1. DocumentAgent\n(get_transaction_bundle + linked docs & NEEDS_REVIEW check)"]
    DOC --> MATCH["2. MatchingAgent\n(3-way bundle completeness: PO / GRNs / Invoices)"]
    MATCH --> RISK["3. RiskAgent\n(evaluate_risks: dupes, split-invoice, MAD price, shared bank, IsolationForest)"]
    RISK --> VEN["4. VendorIntelligenceAgent\n(get_vendor_history: mismatch rate, lead days, small-N guard)"]
    VEN --> GRAPH["5. EvidenceGraphAgent\n(build_transaction_evidence_graph: historical POs & cross-doc links)"]
    GRAPH --> INV["6. InvestigationAgent\n(LLMProvider.explain with <<<UNTRUSTED_DOCUMENT_CONTENT>>> fencing)"]
    INV --> VAL["Post-Validator: validate_evidence_refs()\n(Rejects unknown rule_ids or non-org UUIDs -> 422)"]
    VAL --> AUD["7. AuditAgent\n(Persist DRAFT_READY Investigation + audit_event tool_trace + execution_trace)"]
    AUD --> HUMAN["Human Approver Decision Required\n(human_approval_required = true)"]
```

## 2. Read-Only Finance Copilot (`POST /api/v1/copilot/query`)

```mermaid
flowchart LR
    Q["User Natural-Language Question"] --> GUARD{"Write Verb Guardrail\n(approve, pay, transfer, update, delete...)"}
    GUARD -->|"Matched"| BLOCK["Block + Log COPILOT_WRITE_BLOCKED\nReturn read_only=true"]
    GUARD -->|"Safe Read"| ROUTER["Structured Tool Router\n(Zero Raw SQL)"]
    ROUTER --> T1["query_transaction_by_ref (PO-*/INV-*)"]
    ROUTER --> T2["query_exceptions"]
    ROUTER --> T3["query_vendors"]
    ROUTER --> T4["query_risk_signals"]
    ROUTER --> T5["query_cash_forecast"]
    ROUTER --> T6["query_audit_events"]
    ROUTER --> T7["query_invoices"]
    T1 & T2 & T3 & T4 & T5 & T6 & T7 --> OUT["Grounded Answer + Citations + COPILOT_QUERY Audit"]
```

## 3. Safety & Grounding Invariants
- **Interactive Explorer UI:** Exposed in the frontend at `/agent-harness` (`AgentHarnessPage.tsx`), backed by `GET /api/v1/intelligence/agent-harness`.
- **No payment or approval tools** exist in `ALLOWLISTED_AGENT_TOOLS` (`tools.py`).
- **Prompt injection defense**: Untrusted document/case text is wrapped in `<<<UNTRUSTED_DOCUMENT_CONTENT>>>` markers (`llm/adapter.py`).
- **Zero fabricated citations**: `validate_evidence_refs` (`investigator.py`) verifies every cited UUID against `OrgScopedRepository` before persistence.
- **Provider fallback**: If `gemini`, `groq`, or `ollama` fails or times out, `_HTTPJsonLLMProvider` falls back cleanly without breaking deterministic matching or investigation persistence.
