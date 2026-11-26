# ReconX AI — Neo4j Graph Intelligence Implementation Plan

## 1. Current Architecture Audit
- **PostgreSQL** (`app/models/domain.py`, `app/models/policy.py`, `app/models/audit.py`) stores all authoritative transactional data: organizations, users, vendors, purchase orders, PO lines, GRNs, GRN lines, invoices, invoice lines, documents, reconciliation runs, exception cases, risk signals, investigations, approvals, policies, and append-only audit events.
- **Current Graph Layer** (`app/services/graph/builder.py` + `app/api/v1/intelligence.py`):
  - `GET /api/v1/graph/transactions/{transaction_id}` builds a relational evidence projection on the fly.
  - `GET /api/v1/graph/obligations/{transaction_id}` builds an obligation projection (`Ordered`, `Accepted`, `Invoiced`, `Exposure`) from PostgreSQL.
- **Current Agent Harness** (`app/services/agents/orchestrator.py`, `investigator.py`, `tools.py`):
  - `FinanceOrchestrator` executes 7 sequential deterministic/LLM-assisted stages and persists `execution_trace`, `tool_trace`, and `evidence_refs` inside `Investigation.structured_output_json`.
  - `/agent-harness` currently displays a static 7-stage pipeline diagram plus trace tables.

## 2. Target Architecture (Dual-Engine: PostgreSQL Source of Truth + Neo4j Graph Intelligence)
- **PostgreSQL (Authoritative Transactional Store)**: Continues owning all financial arithmetic (`decimal.Decimal`), reconciliation outcomes, policies, approvals, and immutable audit triggers.
- **Neo4j Community Edition (`neo4j:5.26.2-community`)**: Stores and queries:
  1. Financial Obligation & Evidence Provenance Graph (`Organization`, `Vendor`, `PurchaseOrder`, `POLine`, `GoodsReceipt`, `GRNLine`, `Invoice`, `InvoiceLine`, `Document`, `ReconciliationRun`, `Exception`, `RiskSignal`, `Policy`, `PolicyVersion`, `PolicyEvaluation`, `Investigation`, `Approval`, `AuditEvent`).
  2. Agent Execution Graph (`AgentRun`, `AgentStageExecution`, `AgentDefinition`, `ToolCall`, `EvidenceReference`, `Exception`).
- **Graceful Degradation**: If Neo4j is offline or `GRAPH_BACKEND=relational`, core finance workflows (upload, reconciliation, policy evaluation, brief generation, approvals) continue without error; graph endpoints report degraded status and fall back safely.

## 3. Transactional Outbox & Synchronization Design
- New PostgreSQL table `graph_outbox_event` (Alembic migration `0005_graph_outbox.py`):
  - Columns: `id`, `organization_id`, `event_type`, `entity_type`, `entity_id`, `payload_json`, `status` (`PENDING` | `PROCESSED` | `FAILED`), `attempts`, `last_error_category`, `last_error`, `created_at`, `processed_at`.
- Mutations (reconciliation, document verification, investigation completion, policy evaluation, exception decision, seed/backfill) enqueue outbox events in the **same PostgreSQL transaction**.
- `outbox_worker` (integrated into the background worker loop + on-demand sync) consumes `PENDING` events, applies idempotent `MERGE` Cypher upserts scoped by `organization_id`, and marks events `PROCESSED` (or `FAILED` after bounded retries).

## 4. Neo4j Schema & Tenant Isolation
- Every node carries `organization_id` and `graph_key` (`"{organization_id}:{entity_type}:{source_id}"`) with uniqueness constraints and indexes.
- Every Cypher query is parameterized and filters by `$organization_id`. No raw Cypher endpoint is exposed.
- Monetary values are stored as exact decimal strings (never floats).

## 5. Backend Module Layout
```text
backend/app/services/neo4j/
  __init__.py
  driver.py          # Managed Neo4j driver lifecycle, pool, timeouts
  health.py          # Connectivity & sync status diagnostics
  schema.py          # Idempotent constraints & indexes
  repository.py      # Parameterized Cypher execution helpers
  sync_service.py    # Idempotent MERGE projections for entities & agent runs
  outbox_worker.py   # PostgreSQL graph_outbox_event consumer
  backfill.py        # Full org backfill, tx rebuild, retry failed
  queries/
    obligation_queries.py  # Transaction, vendor, line-level, path traversal
    evidence_queries.py    # Provenance & record-level evidence graph
    vendor_queries.py      # Supplier risk patterns & anomaly connections
    agent_queries.py       # Execution graph, stage/tool/evidence & analytics
```

## 6. Frontend Upgrades
- **`/obligation-graph`**: Multi-view explorer (`Obligation Overview`, `Evidence Provenance`, `Vendor Network`, `Line-Level Fulfilment`), **Explain Financial Relationship** shortest-path finder, **Graph-Based Risk Discovery** panel, Neo4j sync status badge, and authoritative PostgreSQL vs graph property inspector.
- **`/agent-harness`**: Real Neo4j-backed `AgentRun -> AgentStageExecution -> ToolCall -> EvidenceReference` execution graph, Stage & ToolCall inspectors, Cross-Investigation Explorer (vendor investigations, repeated exceptions, failing stages), and Gemini provenance.
