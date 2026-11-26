# ReconX AI — Neo4j Data Model & Cypher Reference

## 1. Node Labels & Tenant Isolation
Every node carries `organization_id` and a unique `graph_key` (`"{organization_id}:{entity_type}:{source_id}"`) enforced by per-label `CREATE CONSTRAINT ... REQUIRE n.graph_key IS UNIQUE` and `CREATE INDEX ... ON (n.organization_id)`.

### Financial Obligation Nodes
`Organization`, `Vendor`, `PurchaseOrder`, `POLine`, `GoodsReceipt`, `GRNLine`, `Invoice`, `InvoiceLine`, `Document`, `ReconciliationRun`, `Exception`, `RiskSignal`, `PolicyVersion`, `PolicyEvaluation`, `Approval`

### Agent Execution Nodes
`AgentRun`, `AgentStageExecution`, `AgentDefinition`, `ToolCall`, `EvidenceReference`, `Investigation`

## 2. Key Relationships
- `(:Organization)-[:HAS_VENDOR]->(:Vendor)`
- `(:Vendor)-[:ISSUED]->(:PurchaseOrder)-[:CONTAINS]->(:POLine)`
- `(:PurchaseOrder)-[:HAS_RECEIPT]->(:GoodsReceipt)-[:CONTAINS]->(:GRNLine)-[:FULFILLS]->(:POLine)`
- `(:Vendor)-[:SENT]->(:Invoice)-[:BILLS_AGAINST]->(:PurchaseOrder)`
- `(:Invoice)-[:CONTAINS]->(:InvoiceLine)-[:CLAIMS_FOR]->(:POLine)`
- `(:PurchaseOrder)-[:EVALUATED_BY]->(:ReconciliationRun)-[:GENERATED]->(:Exception)`
- `(:AgentRun)-[:INVESTIGATES]->(:Exception)`
- `(:AgentRun)-[:EXECUTED_STAGE]->(:AgentStageExecution)-[:CALLED_TOOL]->(:ToolCall)`
- `(:AgentStageExecution)-[:REFERENCED]->(:EvidenceReference)`

## 3. Sample Cypher Queries
```cypher
// Explain shortest financial path within an organization
MATCH (a {organization_id: $org_id, graph_key: $src}),
      (b {organization_id: $org_id, graph_key: $dst}),
      p = shortestPath((a)-[*..8]-(b))
WHERE ALL(n IN nodes(p) WHERE n.organization_id = $org_id)
RETURN nodes(p), relationships(p);

// Cross-investigation vendor pattern discovery
MATCH (v:Vendor {organization_id: $org_id})-[:ISSUED]->(:PurchaseOrder)
      -[:EVALUATED_BY]->(:ReconciliationRun)-[:GENERATED]->(ex:Exception)
      -[:INVESTIGATED_BY]->(ig:Investigation)
RETURN v.label AS vendor, count(DISTINCT ig) AS investigations;
```
