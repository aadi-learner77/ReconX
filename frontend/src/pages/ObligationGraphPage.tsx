import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Network, RefreshCw } from "lucide-react";
import { api } from "../api/client";
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
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("ALL");
  const [viewMode, setViewMode] = useState<"obligation" | "evidence">("obligation");
  const [selectedTxId, setSelectedTxId] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ["obligation-tx-list", search, statusFilter],
    queryFn: () =>
      api.listTransactions({
        q: search,
        status: statusFilter,
        page_size: "50",
      }),
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
    queryFn: () =>
      viewMode === "obligation"
        ? api.getObligationGraph(activeTxId)
        : api.getTransactionGraph(activeTxId),
    enabled: Boolean(activeTxId),
  });

  const rebuildMut = useMutation({
    mutationFn: () => api.rebuildTransactionGraph(activeTxId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["graph-view"] }),
  });

  const rawNodes: any[] = graphData?.nodes || [];
  const rawEdges: any[] = graphData?.edges || [];

  const filteredNodes = useMemo(() => {
    if (entityFilter === "ALL") return rawNodes;
    return rawNodes.filter((n) => n.type === entityFilter);
  }, [rawNodes, entityFilter]);

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const rfNodes: Node[] = useMemo(
    () =>
      filteredNodes.map((n, idx) => {
        const isHighlighted = Boolean(
          selectedNode &&
            (selectedNode.id === n.id ||
              rawEdges.some(
                (e) =>
                  (e.source === selectedNode.id && e.target === n.id) ||
                  (e.target === selectedNode.id && e.source === n.id)
              ))
        );
        return {
          id: n.id,
          position: { x: (idx % 4) * 255, y: Math.floor(idx / 4) * 125 },
          data: { label: `${n.type}: ${n.label}`, raw: n },
          style: flowNodeStyle(n.type, isHighlighted),
        };
      }),
    [filteredNodes, selectedNode, rawEdges]
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      rawEdges
        .filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
        .map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          labelStyle: { fontSize: 10, fill: "var(--ink-500)", fontFamily: "JetBrains Mono, monospace" },
          markerEnd: { type: MarkerType.ArrowClosed },
          style: flowEdgeStyle(false),
        })),
    [rawEdges, visibleNodeIds]
  );

  const entityTypes = useMemo(
    () => ["ALL", ...Array.from(new Set(rawNodes.map((n) => n.type)))],
    [rawNodes]
  );

  const obSummary = (graphData as any)?.summary;

  return (
    <div className="space-y-8">
      <Card variant="hero">
        <PageCaption
          module="Intelligence / Relational Projection"
          index="PostgreSQL Evidence Graph"
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
              Follow every commitment, receipt, invoice claim and approval through a connected
              financial evidence network.
            </p>
          </div>

          <SegmentedControl
            value={viewMode}
            onChange={(val) => {
              setSelectedNode(null);
              setViewMode(val as "obligation" | "evidence");
            }}
            options={[
              { id: "obligation", label: "Obligation View" },
              { id: "evidence", label: "Evidence View" },
            ]}
          />
        </div>
      </Card>

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
      {viewMode === "obligation" && obSummary && obSummary.ordered_qty !== undefined && (
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

      {/* Graph Canvas + Node Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 space-y-3">
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
              <div className="flex flex-wrap gap-3 text-[11px] text-ink-500 pt-1">
                <span>Legend (Left Edge):</span>
                <span className="text-ink-900 font-semibold">■ PO / Obligation</span>
                <span className="text-status-success-fg font-semibold">■ GRN / Approval</span>
                <span className="text-status-warning-fg font-semibold">■ Invoice</span>
                <span className="text-status-danger-fg font-semibold">■ Exception</span>
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
              Click any node in the graph to inspect its authoritative PostgreSQL fields and
              relationships.
            </div>
          )}
          <div className="pt-3 border-t border-sand-200 text-[11px] text-ink-500">
            Payment settlement edges are omitted when no actual payment records exist in the
            database.
          </div>
        </Card>
      </div>
    </div>
  );
};
