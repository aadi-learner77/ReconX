import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Network, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

const NODE_COLORS: Record<string, { bg: string; border: string }> = {
  Supplier: { bg: "#f5f3ff", border: "#8b5cf6" },
  Vendor: { bg: "#f5f3ff", border: "#8b5cf6" },
  PurchaseOrder: { bg: "#eff6ff", border: "#3b82f6" },
  POLine: { bg: "#f8fafc", border: "#94a3b8" },
  DeliveryObligation: { bg: "#ecfeff", border: "#06b6d4" },
  GoodsReceipt: { bg: "#ecfdf5", border: "#10b981" },
  GRNLine: { bg: "#f0fdf4", border: "#22c55e" },
  Invoice: { bg: "#fffbeb", border: "#f59e0b" },
  InvoiceLine: { bg: "#fefce8", border: "#eab308" },
  ReconciliationRun: { bg: "#eef2ff", border: "#6366f1" },
  Exception: { bg: "#fef2f2", border: "#ef4444" },
  Investigation: { bg: "#fdf4ff", border: "#d946ef" },
  Approval: { bg: "#f0fdfa", border: "#14b8a6" },
  RiskSignal: { bg: "#fff7ed", border: "#f97316" },
  HistoricalPO: { bg: "#f1f5f9", border: "#64748b" },
};

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
        page_size: "25",
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
        const c = NODE_COLORS[n.type] || { bg: "#f8fafc", border: "#64748b" };
        const isHighlighted =
          selectedNode &&
          (selectedNode.id === n.id ||
            rawEdges.some(
              (e) =>
                (e.source === selectedNode.id && e.target === n.id) ||
                (e.target === selectedNode.id && e.source === n.id)
            ));
        return {
          id: n.id,
          position: { x: (idx % 4) * 250, y: Math.floor(idx / 4) * 120 },
          data: { label: `${n.type}: ${n.label}`, raw: n },
          style: {
            background: c.bg,
            border: `${isHighlighted ? 3 : 1.5}px solid ${c.border}`,
            borderRadius: 10,
            fontSize: 11,
            fontWeight: 600,
            width: 220,
            padding: 8,
          },
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
          labelStyle: { fontSize: 10, fill: "#475569" },
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: "#94a3b8" },
        })),
    [rawEdges, visibleNodeIds]
  );

  const entityTypes = useMemo(
    () => ["ALL", ...Array.from(new Set(rawNodes.map((n) => n.type)))],
    [rawNodes]
  );

  const obSummary = (graphData as any)?.summary;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-600 mb-1">
            <Network className="w-3.5 h-3.5" />
            <span>Intelligence • PostgreSQL Relational Projection</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Financial Obligation Graph</h1>
          <p className="text-sm text-slate-600 mt-1">
            Follow every commitment, receipt, invoice claim and approval through a connected
            financial evidence network.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg">
          <button
            type="button"
            onClick={() => {
              setSelectedNode(null);
              setViewMode("obligation");
            }}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              viewMode === "obligation"
                ? "bg-white text-indigo-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Obligation View
          </button>
          <button
            type="button"
            onClick={() => {
              setSelectedNode(null);
              setViewMode("evidence");
            }}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              viewMode === "evidence"
                ? "bg-white text-indigo-700 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Evidence View
          </button>
        </div>
      </div>

      {/* Controls & Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search PO, invoice, or supplier..."
          aria-label="Search PO, invoice, or supplier"
          className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs w-56"
        />
        <select
          aria-label="Select transaction"
          value={activeTxId}
          onChange={(e) => {
            setSelectedNode(null);
            setSelectedTxId(e.target.value);
          }}
          className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white max-w-xs"
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
          className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
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
          className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
        >
          <option value="">All Statuses</option>
          <option value="MATCHED">MATCHED</option>
          <option value="EXCEPTION">EXCEPTION</option>
          <option value="INCOMPLETE">INCOMPLETE</option>
        </select>
        <button
          type="button"
          onClick={() => {
            setSearch("");
            setStatusFilter("");
            setEntityFilter("ALL");
            setSelectedNode(null);
          }}
          className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Reset
        </button>
        <button
          type="button"
          onClick={() => {
            refetch();
            if (activeTxId) rebuildMut.mutate();
          }}
          disabled={!activeTxId || rebuildMut.isPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Graph</span>
        </button>
      </div>

      {/* Deterministic Backend Obligation Summary */}
      {viewMode === "obligation" && obSummary && obSummary.ordered_qty !== undefined && (
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
          <div className="p-3 bg-white border border-slate-200 rounded-xl">
            <div className="text-[11px] text-slate-500">Ordered Qty</div>
            <div className="text-base font-bold text-slate-900">{obSummary.ordered_qty}</div>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl">
            <div className="text-[11px] text-slate-500">Accepted Qty</div>
            <div className="text-base font-bold text-emerald-700">{obSummary.accepted_qty}</div>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl">
            <div className="text-[11px] text-slate-500">Invoiced Qty</div>
            <div className="text-base font-bold text-slate-900">{obSummary.invoiced_qty}</div>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl">
            <div className="text-[11px] text-slate-500">Outstanding Delivery</div>
            <div className="text-base font-bold text-slate-900">
              {obSummary.outstanding_delivery_qty}
            </div>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl">
            <div className="text-[11px] text-slate-500">Unsupported Invoiced</div>
            <div className="text-base font-bold text-rose-700">
              {obSummary.unsupported_invoiced_qty}
            </div>
          </div>
          <div className="p-3 bg-white border border-slate-200 rounded-xl">
            <div className="text-[11px] text-slate-500">Exposure ({obSummary.currency})</div>
            <div className="text-base font-bold text-rose-700">{obSummary.exposure_amount}</div>
          </div>
        </div>
      )}

      {/* Graph Canvas + Node Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          {txLoading || graphLoading ? (
            <div className="h-80 flex items-center justify-center text-sm text-slate-500">
              Loading financial graph...
            </div>
          ) : graphError ? (
            <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
              Failed to load graph for selected transaction.
            </div>
          ) : rfNodes.length === 0 ? (
            <div className="h-80 flex items-center justify-center text-sm text-slate-500">
              No matching graph nodes found for current filters.
            </div>
          ) : (
            <>
              <div className="hidden sm:block h-96 border border-slate-200 rounded-lg">
                <ReactFlow
                  nodes={rfNodes}
                  edges={rfEdges}
                  fitView
                  onNodeClick={(_, node) => setSelectedNode((node.data as any)?.raw)}
                >
                  <Background />
                  <Controls />
                </ReactFlow>
              </div>
              {/* Mobile list fallback */}
              <ul className="sm:hidden space-y-2 text-xs">
                {filteredNodes.map((n) => (
                  <li
                    key={n.id}
                    onClick={() => setSelectedNode(n)}
                    className="p-2.5 rounded-lg border border-slate-200 bg-slate-50"
                  >
                    <span className="font-bold text-indigo-700">{n.type}:</span> {n.label}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">Node Detail Inspector</h2>
          {selectedNode ? (
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-indigo-700">{selectedNode.type}</span>
                {selectedNode.data?.status && <StatusBadge value={selectedNode.data.status} />}
              </div>
              <div className="text-sm font-semibold text-slate-900">{selectedNode.label}</div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                {Object.entries(selectedNode.data || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-mono text-slate-800 text-right break-all">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500">
              Click any node in the graph to inspect its authoritative PostgreSQL fields and
              relationships.
            </div>
          )}
          <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500">
            Payment settlement edges are omitted when no actual payment records exist in the
            database.
          </div>
        </div>
      </div>
    </div>
  );
};
