import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

export const TransactionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  const { data: bundle, isLoading, error } = useQuery({
    queryKey: ["transaction", id],
    queryFn: () => api.getTransaction(id!),
    enabled: Boolean(id),
  });

  const { data: graphData } = useQuery({
    queryKey: ["transaction-graph", id],
    queryFn: () => api.getTransactionGraph(id!),
    enabled: Boolean(id),
    retry: false,
  });

  const reconcileMut = useMutation({
    mutationFn: () => api.reconcileTransaction(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transaction", id] });
      qc.invalidateQueries({ queryKey: ["transaction-graph", id] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const riskMut = useMutation({
    mutationFn: () => api.getTransactionRisk(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transaction", id] }),
  });

  if (isLoading) return <div className="text-sm text-slate-500">Loading transaction...</div>;
  if (error || !bundle) {
    return (
      <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
        Transaction not found or unauthorized.
      </div>
    );
  }

  const poLines = bundle.purchase_order?.lines || [];
  const grnLines = bundle.goods_receipts.flatMap((g) => g.lines);
  const invLines = bundle.invoices.flatMap((i) => i.lines);

  const rfNodes: Node[] = (graphData?.nodes || []).map((n: any, idx: number) => ({
    id: n.id,
    position: { x: (idx % 4) * 230, y: Math.floor(idx / 4) * 110 },
    data: { label: `${n.type}: ${n.label}`, raw: n },
  }));
  const rfEdges: Edge[] = (graphData?.edges || []).map((e: any) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: true,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              {bundle.purchase_order?.po_number || `Transaction ${bundle.transaction_id.slice(0, 8)}`}
            </h1>
            <StatusBadge value={bundle.latest_reconciliation?.outcome || bundle.current_status} />
          </div>
          <p className="text-sm text-slate-500 mt-0.5">
            Vendor:{" "}
            <Link to={`/vendors/${bundle.vendor.id}`} className="text-indigo-600 hover:underline">
              {bundle.vendor.legal_name}
            </Link>{" "}
            • Tax ID: {bundle.vendor.tax_identifier || "N/A"}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => riskMut.mutate()}
            className="px-3.5 py-2 border border-slate-300 bg-white rounded-lg text-sm font-medium hover:bg-slate-50"
          >
            Refresh Risk Indicators
          </button>
          {hasPermission("reconciliation:run") && (
            <button
              onClick={() => reconcileMut.mutate()}
              disabled={reconcileMut.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
            >
              {reconcileMut.isPending ? "Reconciling..." : "Reconcile"}
            </button>
          )}
        </div>
      </div>

      {/* Side-by-side PO / GRN / Invoice Header Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-500 uppercase">Purchase Order</div>
          {bundle.purchase_order ? (
            <div className="mt-2 space-y-1 text-sm">
              <div className="font-semibold">{bundle.purchase_order.po_number}</div>
              <div>Date: {bundle.purchase_order.issue_date}</div>
              <div className="font-mono">
                Total: {bundle.purchase_order.currency} {bundle.purchase_order.total_amount}
              </div>
            </div>
          ) : (
            <div className="mt-2 text-sm text-amber-700 font-medium">Missing PO</div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-500 uppercase">
            Goods Receipts ({bundle.goods_receipts.length})
          </div>
          {bundle.goods_receipts.length ? (
            <ul className="mt-2 space-y-1 text-sm">
              {bundle.goods_receipts.map((g) => (
                <li key={g.id} className="flex justify-between">
                  <span className="font-medium">{g.grn_number}</span>
                  <span className="text-slate-600">
                    Acc: {g.lines.reduce((s, l) => s + Number(l.accepted_qty), 0)} | Rej:{" "}
                    {g.lines.reduce((s, l) => s + Number(l.rejected_qty), 0)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-2 text-sm text-amber-700 font-medium">No GRNs recorded</div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-500 uppercase">
            Supplier Invoices ({bundle.invoices.length})
          </div>
          {bundle.invoices.map((inv) => (
            <div key={inv.id} className="mt-2 text-sm border-t pt-1 first:border-t-0 first:pt-0">
              <div className="font-semibold">{inv.invoice_number}</div>
              <div className="font-mono">
                Total: {inv.currency} {inv.total_amount} (Tax: {inv.tax_amount})
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Line-level Side-by-Side Comparison */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm overflow-x-auto">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">
          Side-by-Side Line Comparison (PO vs GRN Accepted vs Invoiced)
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b">
              <th className="py-2">Item</th>
              <th className="py-2">PO Qty / Price</th>
              <th className="py-2">GRN Accepted / Rej</th>
              <th className="py-2">Invoiced Qty / Price</th>
              <th className="py-2">Difference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {poLines.map((pl) => {
              const acc = grnLines
                .filter((g) => g.po_line_id === pl.id || g.item_code === pl.item_code)
                .reduce((s, g) => s + Number(g.accepted_qty), 0);
              const rej = grnLines
                .filter((g) => g.po_line_id === pl.id || g.item_code === pl.item_code)
                .reduce((s, g) => s + Number(g.rejected_qty), 0);
              const matchedInvs = invLines.filter(
                (i) => i.po_line_id === pl.id || i.item_code === pl.item_code
              );
              const invQty = matchedInvs.reduce((s, i) => s + Number(i.quantity), 0);
              const invPrice = matchedInvs[0]?.unit_price || "—";
              const qtyDiff = invQty - acc;
              const hasDiff = qtyDiff !== 0 || (invPrice !== "—" && Number(invPrice) !== Number(pl.unit_price));
              return (
                <tr key={pl.id} className={hasDiff ? "bg-rose-50/70" : ""}>
                  <td className="py-2 font-medium">
                    {pl.item_code} — {pl.description}
                  </td>
                  <td className="py-2 font-mono">
                    {pl.quantity} {pl.uom} @ {pl.unit_price}
                  </td>
                  <td className="py-2 font-mono">
                    {acc} {pl.uom} (Rej {rej})
                  </td>
                  <td className="py-2 font-mono">
                    {invQty} {pl.uom} @ {invPrice}
                  </td>
                  <td className="py-2 font-mono text-xs">
                    {hasDiff ? `Qty Δ=${qtyDiff}` : "Exact"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Rule-by-rule breakdown */}
      {bundle.latest_reconciliation && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm overflow-x-auto">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h2 className="text-sm font-semibold text-slate-900">
              Deterministic Rule Breakdown (v{bundle.latest_reconciliation.rule_version})
            </h2>
            <div className="text-xs font-mono text-slate-700">
              Undisputed: {String(bundle.latest_reconciliation.totals.undisputed_amount || "0")} |
              Disputed: {String(bundle.latest_reconciliation.totals.disputed_amount || "0")}
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b">
                <th className="py-2">Rule ID</th>
                <th className="py-2">Field</th>
                <th className="py-2">Expected</th>
                <th className="py-2">Actual</th>
                <th className="py-2">Variance</th>
                <th className="py-2">Tolerance</th>
                <th className="py-2">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bundle.latest_reconciliation.results.map((r) => (
                <tr key={r.id}>
                  <td className="py-2 font-mono font-semibold">{r.rule_id}</td>
                  <td className="py-2">{r.field_name}</td>
                  <td className="py-2 font-mono text-xs">{r.expected_value}</td>
                  <td className="py-2 font-mono text-xs">{r.actual_value}</td>
                  <td className="py-2 font-mono text-xs">{r.variance}</td>
                  <td className="py-2 text-xs text-slate-600">{r.tolerance_applied}</td>
                  <td className="py-2">
                    <StatusBadge value={r.result} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Exceptions & Risk Indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">
            Exceptions ({bundle.exceptions.length})
          </h2>
          {bundle.exceptions.length === 0 ? (
            <div className="text-sm text-slate-500">No exceptions for this transaction.</div>
          ) : (
            <ul className="space-y-2">
              {bundle.exceptions.map((e) => (
                <li key={e.id} className="p-3 rounded-lg border border-slate-200 flex justify-between gap-2">
                  <div>
                    <Link
                      to={`/exceptions/${e.id}`}
                      className="text-sm font-semibold text-indigo-600 hover:underline"
                    >
                      {e.type} ({e.rule_id})
                    </Link>
                    <p className="text-xs text-slate-600 mt-0.5">{e.summary}</p>
                  </div>
                  <StatusBadge value={e.status} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-1">Risk Indicators</h2>
          <p className="text-xs text-slate-500 mb-3">
            Explainable risk indicators for human review — not proof of fraud.
          </p>
          {bundle.risk_signals.length === 0 ? (
            <div className="text-sm text-slate-500">No risk signals recorded.</div>
          ) : (
            <ul className="space-y-2">
              {bundle.risk_signals.map((s) => (
                <li key={s.id} className="p-3 rounded-lg border border-amber-200 bg-amber-50/50 text-xs">
                  <div className="flex justify-between font-semibold text-slate-800">
                    <span>{s.signal_type}</span>
                    <span>Score: {s.score}</span>
                  </div>
                  <div className="text-slate-600 mt-1">
                    {(s.reason.contributing_signals || []).join("; ")}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Relational Financial Evidence Graph (D2, React Flow) */}
      {graphData && rfNodes.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-slate-900">
              Financial Evidence Graph (PostgreSQL Relational Projection)
            </h2>
            {selectedNode && (
              <span className="text-xs text-indigo-700 font-mono">
                Selected: {selectedNode.type} — {selectedNode.label}
              </span>
            )}
          </div>
          <div className="h-72 border border-slate-200 rounded-lg">
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
        </div>
      )}
    </div>
  );
};
