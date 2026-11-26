# ReconX AI — Judge-Ready Neo4j Live Demonstration

1. **Verify Neo4j Health**: Open `/obligation-graph` as `admin@reconx-demo.com` and point to the `CURRENT` Neo4j sync status bar (`Nodes` & `Relationships` count).
2. **Demo 1 — Obligation Graph (`PO-2026-0002`, AT-02)**:
   - Show `Ordered Qty: 100`, `Accepted Qty: 90`, `Unsupported Invoiced: 10`, `Exposure: ₹1,200.00`.
   - Use **Explain Financial Relationship**: select `Vendor: Sahyadri Industrial Fasteners LLP` → `Exception: QTY_OVER_BILLED (R-QTY-01)` → click **Explain Path** to show the live Neo4j `shortestPath` hops.
3. **Demo 2 — Multi-GRN (`PO-2026-0003`, AT-03)**:
   - Select `PO-2026-0003` and switch to **Line Fulfilment** view to show both `GRN-2026-0003A` (`60`) and `GRN-2026-0003B` (`40`) aggregating cleanly to `100` without double-counting.
4. **Demo 3 — Agent Execution Graph (`/agent-harness`)**:
   - Run an investigation on an exception, then open `/agent-harness`.
   - Point to the live Neo4j `AgentRun -> AgentStageExecution -> ToolCall & EvidenceReference` graph, click nodes to inspect real stage durations/tools, and inspect **Cross-Investigation Relationship Explorer**.
