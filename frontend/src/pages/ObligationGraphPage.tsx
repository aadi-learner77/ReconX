import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { GitBranch, Network, RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Button,
  Card,
  EmptyState,
  PageCaption,
  PageSkeleton,
  SegmentedControl,
  Stat,
  StatusPill,
} from "../components/ui";
import { flowControlStyle, flowEdgeStyle, flowNodeStyle } from "../theme/flowTheme";
import { formatInrString } from "../utils/money";

export const ObligationGraphPage: React.FC = () => {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("ALL");
  const [viewMode, setViewMode] = useState<"overview" | "evidence" | "vendor" | "fulfilment">("overview");
  const [selectedTxId, setSelectedTxId] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [nodeFocusQuery, setNodeFocusQuery] = useState("");
  const [pathSrc, setPathSrc] = useState<string>("");
  const [pathDst, setPathDst] = useState<string>("");
  const [pathResult, setPathResult] = useState<any | null>(null);

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ["obligation-tx-list", search, statusFilter],
    queryFn: () =>
      api.listTransactions({
        q: search,
        status: statusFilter,
        page_size: "50",
      }),
  });

  const { data: graphHealth, refetch: refetchHealth } = useQuery({
    queryKey: ["graph-health"],
    queryFn: api.getGraphHealth,
  });

  const { data: riskDiscovery } = useQuery({
    queryKey: ["graph-risk-discovery"],
    queryFn: api.getGraphRiskDiscovery,
  });

  const transactions = txData?.items || [];
  const activeTxId = useMemo(() => {
    if (selectedTxId && transactions.some((t) => t.transaction_id === selectedTxId)) {
      return selectedTxId;
    }
    const at02 = transactions.find((t) => t.scenario_label === "AT-02");
    return at02?.transaction_id || transactions[0]?.transaction_id || "";
  }, [transactions, selectedTxId]);

  const {
    data: graphData,
    isLoading: graphLoading,
    error: graphError,
    refetch,
  } = useQuery({
    queryKey: ["graph-view", viewMode, activeTxId],
    queryFn: () => api.getObligationGraph(activeTxId, viewMode),
    enabled: Boolean(activeTxId),
  });

  const rebuildMut = useMutation({
    mutationFn: () => api.rebuildTransactionGraph(activeTxId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["graph-view"] });
      refetchHealth();
    },
  });

  const backfillMut = useMutation({
    mutationFn: api.backfillGraph,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["graph-view"] });
      qc.invalidateQueries({ queryKey: ["graph-risk-discovery"] });
      refetchHealth();
    },
  });

  const pathMut = useMutation({
    mutationFn: () => api.getRelationshipPath(pathSrc, pathDst),
    onSuccess: (res) => setPathResult(res),
  });

  const rawNodes: any[] = graphData?.nodes || [];
  const rawEdges: any[] = graphData?.edges || [];

  const pathNodeIds = useMemo(
    () => new Set((pathResult?.nodes || []).map((n: any) => n.id)),
    [pathResult]
  );
  const pathEdgeIds = useMemo(
    () => new Set((pathResult?.edges || []).map((e: any) => e.id)),
    [pathResult]
  );

  const filteredNodes = useMemo(() => {
    if (entityFilter === "ALL") return rawNodes;
    return rawNodes.filter((n) => n.type === entityFilter);
  }, [rawNodes, entityFilter]);

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const rfNodes: Node[] = useMemo(() => {
    const laneX = (t: string): number => {
      const up = t.toUpperCase();
      if (up.includes("VENDOR")) return 0;
      if (up.includes("PURCHASEORDER") || up === "PO" || up.includes("POLINE")) return 280;
      if (up.includes("GOODSRECEIPT") || up.includes("GRN") || up.includes("DOCUMENT")) return 570;
      if (up.includes("INVOICE") || up.includes("RECONCILIATION")) return 860;
      return 1150;
    };
    const laneCounts: Record<number, number> = {};
    const focusQ = nodeFocusQuery.trim().toLowerCase();

    return filteredNodes.map((n) => {
      const x = laneX(n.type || "");
      const row = laneCounts[x] || 0;
      laneCounts[x] = row + 1;

      const amt = Number(n.data?.exposure_amount || n.data?.total_amount || 0);
      const width = amt >= 100000 ? 270 : amt >= 25000 ? 245 : 220;

      const focusMatch =
        Boolean(focusQ) &&
        (`${n.type} ${n.label} ${n.source_id || ""}`.toLowerCase().includes(focusQ));

      const activeId = hoveredNodeId || selectedNode?.id;
      const isConnected = Boolean(
        activeId &&
          (activeId === n.id ||
            rawEdges.some(
              (e) =>
                (e.source === activeId && e.target === n.id) ||
                (e.target === activeId && e.source === n.id)
            ))
      );
      const isHighlighted = Boolean(pathNodeIds.has(n.id) || isConnected || focusMatch);
      const dimmed = Boolean((hoveredNodeId || focusQ) && !isHighlighted);

      return {
        id: n.id,
        position: { x, y: row * 118 },
        data: { label: `${n.type}: ${n.label}`, raw: n },
        style: {
          ...flowNodeStyle(n.type, isHighlighted),
          width,
          opacity: dimmed ? 0.28 : 1,
          transition: "opacity 160ms ease, box-shadow 160ms ease",
        },
      };
    });
  }, [filteredNodes, selectedNode, hoveredNodeId, nodeFocusQuery, rawEdges, pathNodeIds]);

  const rfEdges: Edge[] = useMemo(() => {
    const activeId = hoveredNodeId || selectedNode?.id;
    return rawEdges
      .filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
      .map((e) => {
        const isConn = Boolean(activeId && (e.source === activeId || e.target === activeId));
        const inPath = pathEdgeIds.has(e.id);
        const amt = Number(e.data?.amount || e.data?.total_amount || 0);
        const baseWidth = amt >= 100000 ? 3.5 : amt >= 25000 ? 2.5 : 1.5;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          animated: inPath || isConn,
          labelStyle: { fontSize: 10, fill: "var(--ink-500)", fontFamily: "JetBrains Mono, monospace" },
          markerEnd: { type: MarkerType.ArrowClosed },
          style: {
            ...flowEdgeStyle(inPath || isConn),
            strokeWidth: inPath || isConn ? Math.max(baseWidth, 2.5) : baseWidth,
            opacity: hoveredNodeId && !isConn ? 0.2 : 1,
          },
        };
      });
  }, [rawEdges, visibleNodeIds, pathEdgeIds, hoveredNodeId, selectedNode]);

  const entityTypes = useMemo(
    () => ["ALL", ...Array.from(new Set(rawNodes.map((n) => n.type)))],
    [rawNodes]
  );

  const obSummary = (graphData as any)?.summary;

  return (
    <div className="space-y-8">
      <Card variant="hero">
        <PageCaption
          module="Intelligence / Neo4j Graph Engine"
          index={
            graphData?.source === "neo4j"
              ? "Live Neo4j Cypher"
              : "PostgreSQL Relational Projection"
          }
        />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 mb-1">
              <Network className="w-3.5 h-3.5 text-ink-900" />
              <span>Commitment → Delivery → Claim</span>
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-bold text-ink-900">
              Financial Obligation Graph
            </h1>
            <p className="text-sm text-ink-700 mt-1">
              Neo4j-backed relationship traversal across suppliers, PO lines, multi-GRN receipts,
              invoices, exceptions, and investigations.
            </p>
          </div>

          <SegmentedControl
            value={viewMode}
            onChange={(val) => {
              setSelectedNode(null);
              setPathResult(null);
              setViewMode(val as "overview" | "evidence" | "vendor" | "fulfilment");
            }}
            options={[
              { id: "overview", label: "Obligation View" },
              { id: "evidence", label: "Evidence View" },
              { id: "vendor", label: "Vendor Network" },
              { id: "fulfilment", label: "Line Fulfilment" },
            ]}
          />
        </div>
      </Card>

      {/* Neo4j Sync & Connectivity Bar */}
      {graphHealth && (
        <Card variant="subtle" className="py-3 px-4 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill
              value={graphHealth.sync_state}
              tone={
                graphHealth.sync_state === "CURRENT"
                  ? "success"
                  : graphHealth.sync_state === "DEGRADED"
                    ? "danger"
                    : "warning"
              }
            />
            <span className="font-mono text-ink-700">
              Backend: <strong>{graphHealth.graph_backend}</strong> • Nodes:{" "}
              <strong>{graphHealth.nodes_synchronized}</strong> • Relationships:{" "}
              <strong>{graphHealth.relationships_synchronized}</strong> • Pending Outbox:{" "}
              <strong>{graphHealth.pending_events}</strong>
            </span>
          </div>
          {hasPermission("admin:config:write") && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => backfillMut.mutate()}
              disabled={backfillMut.isPending}
            >
              {backfillMut.isPending ? "Syncing Neo4j..." : "Backfill Neo4j Graph"}
            </Button>
          )}
        </Card>
      )}

      {/* Controls & Filters */}
      <Card className="flex flex-wrap items-center gap-3 p-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search PO, invoice, or supplier..."
          aria-label="Search PO, invoice, or supplier"
          className="px-3 py-2 rounded-control border border-sand-200 bg-sand-50 text-xs text-ink-900 w-56"
        />
        <select
          aria-label="Select transaction"
          value={activeTxId}
          onChange={(e) => {
            setSelectedNode(null);
            setPathResult(null);
            setSelectedTxId(e.target.value);
          }}
          className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900 max-w-xs"
        >
          {transactions.map((t) => (
            <option key={t.transaction_id} value={t.transaction_id}>
              {t.po_number || t.transaction_id.slice(0, 8)} — {t.vendor_name} (
              {t.latest_outcome || t.status})
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by entity type"
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
          className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900"
        >
          {entityTypes.map((et) => (
            <option key={et} value={et}>
              Entity: {et}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by reconciliation status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900"
        >
          <option value="">All Statuses</option>
          <option value="MATCHED">MATCHED</option>
          <option value="EXCEPTION">EXCEPTION</option>
          <option value="INCOMPLETE">INCOMPLETE</option>
        </select>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setSearch("");
            setStatusFilter("");
            setEntityFilter("ALL");
            setSelectedNode(null);
            setPathResult(null);
          }}
        >
          Reset
        </Button>
        <Button
          size="sm"
          onClick={() => {
            refetch();
            if (activeTxId) rebuildMut.mutate();
          }}
          disabled={!activeTxId || rebuildMut.isPending}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Graph</span>
        </Button>
      </Card>

      {/* Deterministic Backend Obligation Summary */}
      {obSummary && obSummary.ordered_qty !== undefined && (
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
          <Stat label="Ordered Qty" value={obSummary.ordered_qty} mono className="p-4" />
          <Stat label="Accepted Qty" value={obSummary.accepted_qty} mono tone="success" className="p-4" />
          <Stat label="Invoiced Qty" value={obSummary.invoiced_qty} mono className="p-4" />
          <Stat label="Outstanding" value={obSummary.outstanding_delivery_qty} mono className="p-4" />
          <Stat
            label="Unsupported"
            value={obSummary.unsupported_invoiced_qty}
            mono
            tone="danger"
            className="p-4"
          />
          <Stat
            label={`Exposure (${obSummary.currency})`}
            value={formatInrString(String(obSummary.exposure_amount || "0.00"), obSummary.currency)}
            mono
            tone="danger"
            className="p-4"
          />
        </div>
      )}

      {/* Explain Financial Relationship (Neo4j shortestPath) */}
      {rawNodes.length >= 2 && (
        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-ink-900" />
              <h2 className="font-display text-base font-bold text-ink-900">
                Explain Financial Relationship (Neo4j Shortest Path)
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <select
                aria-label="Path source node"
                value={pathSrc}
                onChange={(e) => setPathSrc(e.target.value)}
                className="px-2.5 py-1.5 rounded-control border border-sand-200 bg-sand-50 max-w-[200px]"
              >
                <option value="">Select Start Node...</option>
                {rawNodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.type}: {n.label}
                  </option>
                ))}
              </select>
              <span className="text-ink-500">→</span>
              <select
                aria-label="Path target node"
                value={pathDst}
                onChange={(e) => setPathDst(e.target.value)}
                className="px-2.5 py-1.5 rounded-control border border-sand-200 bg-sand-50 max-w-[200px]"
              >
                <option value="">Select Target Node...</option>
                {rawNodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.type}: {n.label}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                disabled={!pathSrc || !pathDst || pathMut.isPending}
                onClick={() => pathMut.mutate()}
              >
                {pathMut.isPending ? "Traversing..." : "Explain Path"}
              </Button>
            </div>
          </div>

          {pathResult && (
            <div className="p-3.5 rounded-control bg-sand-50 border border-sand-200 text-xs space-y-2">
              {!pathResult.path_found ? (
                <div className="text-ink-700">{pathResult.message}</div>
              ) : (
                <div className="space-y-1.5 font-mono">
                  <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500 font-sans font-semibold">
                    Verified Shortest Path ({pathResult.steps.length} hop(s) via Neo4j)
                  </div>
                  {pathResult.steps.map((st: any, idx: number) => (
                    <div key={idx} className="flex flex-wrap items-center gap-2 text-ink-900">
                      <span className="px-2 py-0.5 rounded bg-paper border border-sand-200">
                        {st.from_type}: {st.from_label}
                      </span>
                      <span className="text-ink-500 font-semibold">—[{st.relationship}]→</span>
                      <span className="px-2 py-0.5 rounded bg-paper border border-sand-200">
                        {st.to_type}: {st.to_label}
                      </span>
                      <StatusPill value={st.verified ? "VERIFIED" : "INFERRED"} tone={st.verified ? "success" : "warning"} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Graph Canvas + Node Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 space-y-3">
          {/* Graph Legend & Search-to-Focus Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-sand-200">
            <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-ink-500">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-ink-900" /> Vendor / PO
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-status-success-fg" /> GRN / Approval
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-status-warning-fg" /> Invoice
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-status-danger-fg" /> Exception
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-status-info-fg" /> Investigation
              </span>
            </div>
            <input
              aria-label="Search node to focus"
              value={nodeFocusQuery}
              onChange={(e) => setNodeFocusQuery(e.target.value)}
              placeholder="Search node to focus..."
              className="px-2.5 py-1 rounded-control border border-sand-200 bg-sand-50 text-xs font-mono text-ink-900 w-48"
            />
          </div>
          {txLoading || graphLoading ? (
            <PageSkeleton />
          ) : graphError ? (
            <div className="p-4 rounded-control bg-status-danger-bg text-sm text-status-danger-fg">
              Failed to load graph for selected transaction.
            </div>
          ) : rfNodes.length === 0 ? (
            <EmptyState
              title="No matching graph nodes"
              description="Reset entity or status filters to inspect the full obligation graph."
            />
          ) : (
            <>
              <div className="hidden sm:block h-[440px] border border-sand-200 rounded-card bg-sand-50 overflow-hidden">
                <ReactFlow
                  nodes={rfNodes}
                  edges={rfEdges}
                  fitView
                  fitViewOptions={{ padding: 0.18 }}
                  onNodeClick={(_, node) => setSelectedNode((node.data as any)?.raw)}
                  onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
                  onNodeMouseLeave={() => setHoveredNodeId(null)}
                >
                  <Background color="var(--sand-200)" gap={18} />
                  <Controls style={flowControlStyle} />
                  <MiniMap style={flowControlStyle} nodeColor="var(--sand-300)" />
                </ReactFlow>
              </div>
              <ul className="sm:hidden space-y-2 text-xs">
                {filteredNodes.map((n) => (
                  <li
                    key={n.id}
                    onClick={() => setSelectedNode(n)}
                    className="p-2.5 rounded-control border border-sand-200 bg-sand-50"
                  >
                    <span className="font-mono font-bold text-ink-900">{n.type}:</span> {n.label}
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap justify-between gap-3 text-[11px] text-ink-500 pt-1">
                <div className="flex flex-wrap gap-3">
                  <span>Legend (Left Edge):</span>
                  <span className="text-ink-900 font-semibold">■ PO / Obligation</span>
                  <span className="text-status-success-fg font-semibold">■ GRN / Approval</span>
                  <span className="text-status-warning-fg font-semibold">■ Invoice</span>
                  <span className="text-status-danger-fg font-semibold">■ Exception</span>
                </div>
                <span className="font-mono">Source: {graphData?.source || "neo4j"}</span>
              </div>
            </>
          )}
        </Card>

        <Card className="space-y-3">
          <h2 className="font-display text-lg font-bold text-ink-900">Node Detail Inspector</h2>
          {selectedNode ? (
            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-ink-900">{selectedNode.type}</span>
                {selectedNode.data?.status && <StatusPill value={selectedNode.data.status} />}
              </div>
              <div className="text-sm font-semibold text-ink-900">{selectedNode.label}</div>
              <div className="p-3 rounded-control bg-sand-50 border border-sand-200 space-y-1.5">
                {Object.entries(selectedNode.data || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-ink-500">{k}</span>
                    <span className="font-mono text-ink-900 text-right break-all">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-xs text-ink-500">
              Click any node in the graph to inspect its Neo4j properties and source-linked
              PostgreSQL identifiers.
            </div>
          )}
          <div className="pt-3 border-t border-sand-200 text-[11px] text-ink-500">
            Payment settlement edges are omitted when no actual payment records exist in
            PostgreSQL.
          </div>
        </Card>
      </div>

      {/* Graph-Based Risk Discovery */}
      {riskDiscovery && (
        <Card className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-status-info-fg" />
              <h2 className="font-display text-lg font-bold text-ink-900">
                Graph-Based Risk Discovery (Neo4j Pattern Traversal)
              </h2>
            </div>
            <StatusPill value={riskDiscovery.disclaimer} tone="info" />
          </div>
          {!riskDiscovery.patterns?.length ? (
            <div className="text-xs text-ink-500">
              {riskDiscovery.degraded
                ? "Neo4j is currently unavailable for cross-transaction pattern discovery."
                : "No multi-transaction anomaly patterns detected in current graph."}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              {riskDiscovery.patterns.slice(0, 6).map((pat: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-card bg-sand-50 border border-sand-200 space-y-1"
                >
                  <div className="font-mono text-[10px] uppercase text-status-info-fg font-semibold">
                    {pat.pattern_type}
                  </div>
                  <div className="font-semibold text-ink-900">{pat.title}</div>
                  <div className="font-mono text-ink-700">{pat.evidence}</div>
                  <div className="text-[11px] text-ink-500 pt-1">{pat.limitation}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
