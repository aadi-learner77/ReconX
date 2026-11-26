# ReconX AI — Neo4j Graph Architecture

## 1. Why Neo4j Was Introduced
ReconX AI handles multi-hop procurement and payables chains (`Vendor -> PurchaseOrder -> POLine <- GRNLine <- GoodsReceipt`, `Invoice -> PurchaseOrder`, `ReconciliationRun -> Exception -> Investigation -> AgentStageExecution -> ToolCall -> EvidenceReference`). While PostgreSQL excels at transactional integrity and `decimal.Decimal` arithmetic, Neo4j provides native graph traversal for:
- **Multi-hop shortest-path explanations** (`Explain Financial Relationship`)
- **Cross-transaction supplier anomaly discovery** (repeated exceptions, multi-invoice POs, incomplete delivery chains)
- **Real AI-agent execution lineage** (`AgentRun -> AgentStageExecution -> ToolCall -> EvidenceReference`).

## 2. PostgreSQL vs Neo4j Responsibilities
- **PostgreSQL (Authoritative Source of Truth)**: Owns organizations, users, RBAC, vendors, POs, GRNs, invoices, documents, `decimal.Decimal` reconciliation runs, exceptions, approvals, policies, executive briefs, and trigger-protected `audit_event`.
- **Neo4j Community Edition (`neo4j:5.26.2-community`)**: Graph intelligence & traversal projection synchronized from PostgreSQL via the `graph_outbox_event` transactional outbox.

## 3. Synchronization & Graceful Degradation
1. Domain mutations (reconciliation, investigation completion) write a `PENDING` `graph_outbox_event` row in the **same PostgreSQL transaction**.
2. `outbox_worker.py` drains `PENDING` events using idempotent `MERGE` Cypher queries scoped by `organization_id`.
3. If Neo4j is temporarily offline, finance workflows (uploads, reconciliation, approvals, briefs) continue unaffected in PostgreSQL, and `/api/v1/graph/health` surfaces `DEGRADED` / `STALE` status.
