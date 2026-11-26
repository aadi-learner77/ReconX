import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowUpRight, Sparkles } from "lucide-react";
import { api } from "../api/client";
import {
  Card,
  DataTable,
  EmptyState,
  PageCaption,
  PageSkeleton,
  Stat,
  StatusPill,
} from "../components/ui";
import { chartTheme, outcomeBarColor } from "../theme/chartTheme";

export const DashboardPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.dashboardSummary,
  });

  if (isLoading) return <PageSkeleton />;
  if (error || !data) {
    return (
      <Card className="border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-sm">
        Failed to load dashboard metrics.
      </Card>
    );
  }

  const totalTx = data.kpis.transactions || 0;
  const matchedRate =
    totalTx > 0 ? `${Math.round((data.kpis.matched_cases / totalTx) * 100)}%` : "0%";

  return (
    <div className="space-y-10">
      {/* Hero Band */}
      <Card variant="hero">
        <PageCaption
          project="ReconX AI / Operations Console"
          module="Module / Finance Operations"
          index={`Active Tx / ${data.kpis.transactions}`}
        />
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="font-display text-3xl md:text-5xl font-bold text-ink-900">
              Finance Operations Dashboard
            </h1>
            <p className="text-sm md:text-base text-ink-700 mt-2 max-w-2xl">
              Three-way Purchase Order, Goods-Receipt &amp; Supplier Invoice reconciliation ledger.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/documents"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-control bg-ink-900 text-on-ink text-sm font-medium hover:-translate-y-px transition-transform shadow-soft"
            >
              <span>Upload Documents</span>
              <ArrowUpRight className="w-4 h-4" />
            </Link>
            <Link
              to="/transactions"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-control border border-ink-900 text-ink-900 text-sm font-medium hover:bg-sand-100 transition-colors"
            >
              <span>View Transactions</span>
            </Link>
          </div>
        </div>
      </Card>

      {/* Hero KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <Stat label="Matched Rate" value={matchedRate} tone="success" hint={`${data.kpis.matched_cases} matched`} />
        <Stat label="Documents" value={data.kpis.documents} />
        <Stat label="Transactions" value={data.kpis.transactions} />
        <Stat label="Open Exceptions" value={data.kpis.open_exceptions} tone="danger" />
        <Stat label="Pending Approvals" value={data.kpis.pending_approvals} tone="warning" />
        <Stat label="Processing Jobs" value={data.kpis.processing_jobs} />
      </div>

      {/* Outcomes Chart + Exception Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-lg font-bold text-ink-900">Reconciliation Outcomes</h2>
            <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
              Deterministic Engine
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.outcome_breakdown}>
                <CartesianGrid vertical={false} stroke={chartTheme.gridStroke} />
                <XAxis dataKey="outcome" tick={chartTheme.axisTick} stroke={chartTheme.axisStroke} />
                <YAxis allowDecimals={false} tick={chartTheme.axisTick} stroke={chartTheme.axisStroke} />
                <Tooltip contentStyle={chartTheme.tooltipStyle} />
                <Bar dataKey="count" radius={chartTheme.barRadius}>
                  {data.outcome_breakdown.map((entry: any) => (
                    <Cell key={entry.outcome} fill={outcomeBarColor(entry.outcome)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-lg font-bold text-ink-900">Exception Queue</h2>
            <Link to="/exceptions" className="text-xs font-semibold text-ink-900 underline">
              View all
            </Link>
          </div>
          {data.exception_queue.length === 0 ? (
            <EmptyState
              title="No Open Exceptions"
              description="Run reconciliation on transactions to inspect variances."
            />
          ) : (
            <ul className="divide-y divide-sand-200">
              {data.exception_queue.map((e) => (
                <li key={e.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      to={`/exceptions/${e.id}`}
                      className="text-sm font-semibold text-ink-900 hover:underline truncate block"
                    >
                      {e.type}
                    </Link>
                    <p className="text-xs text-ink-500 truncate mt-0.5">{e.summary}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusPill value={e.severity} />
                    <StatusPill value={e.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Gemini Intelligence Showcase Card */}
      <Card variant="subtle" className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
            <Sparkles className="w-3.5 h-3.5 text-ink-900" aria-hidden="true" />
            <span>AI Assistance Powered by Google Gemini API</span>
          </div>
          <h2 className="font-display text-xl font-bold text-ink-900">
            Gemini-Powered Financial Intelligence
          </h2>
          <p className="text-xs text-ink-700 max-w-2xl">
            Google Gemini assists ReconX in contextual investigation while deterministic matching and
            evidence validation preserve financial correctness.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="px-3.5 py-2 rounded-control bg-paper border border-sand-200 font-mono">
            Provider:{" "}
            <strong className="uppercase text-ink-900">
              {data.ai_status?.configured_provider || "mock"}
            </strong>{" "}
            ({data.ai_status?.gemini_model || "gemini-2.5-flash"})
          </div>
          <Link
            to="/agent-harness"
            className="px-4 py-2 rounded-control border border-ink-900 text-ink-900 font-semibold hover:bg-paper transition-colors"
          >
            Open Agent Harness →
          </Link>
        </div>
      </Card>

      {/* Recent Audit Activity */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl font-bold text-ink-900">Recent Audit Activity</h2>
          <Link to="/audit" className="text-xs font-semibold text-ink-900 underline">
            Open Audit Explorer
          </Link>
        </div>
        <DataTable
          rowKey={(a) => a.id}
          rows={data.recent_activity}
          columns={[
            { key: "action", header: "Action", render: (a) => <span className="font-semibold">{a.action}</span> },
            { key: "entity", header: "Entity", mono: true, render: (a) => a.entity_type },
            { key: "actor", header: "Actor", mono: true, render: (a) => a.actor_type },
            {
              key: "ts",
              header: "Timestamp",
              mono: true,
              align: "right",
              render: (a) => new Date(a.timestamp).toLocaleString(),
            },
          ]}
        />
      </div>
    </div>
  );
};
