import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export const DashboardPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.dashboardSummary,
  });

  if (isLoading) return <div className="text-sm text-slate-500">Loading dashboard...</div>;
  if (error || !data) {
    return (
      <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
        Failed to load dashboard metrics.
      </div>
    );
  }

  const kpis = [
    { label: "Documents", value: data.kpis.documents },
    { label: "Transactions", value: data.kpis.transactions },
    { label: "Matched Cases", value: data.kpis.matched_cases },
    { label: "Open Exceptions", value: data.kpis.open_exceptions },
    { label: "Pending Approvals", value: data.kpis.pending_approvals },
    { label: "Processing Jobs", value: data.kpis.processing_jobs },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Finance Operations Dashboard</h1>
          <p className="text-sm text-slate-500">
            Three-way PO, GRN & invoice reconciliation overview
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/documents"
            className="px-3.5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
          >
            Upload Documents
          </Link>
          <Link
            to="/transactions"
            className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50"
          >
            View Transactions
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">{k.label}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{k.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Reconciliation Outcomes</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.outcome_breakdown}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="outcome" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#4f46e5" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-900">Exception Queue</h2>
            <Link to="/exceptions" className="text-xs text-indigo-600 hover:underline">
              View all
            </Link>
          </div>
          {data.exception_queue.length === 0 ? (
            <div className="text-sm text-slate-500 py-8 text-center">
              No open exceptions. Run reconciliation on transactions to inspect variances.
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.exception_queue.map((e) => (
                <li key={e.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      to={`/exceptions/${e.id}`}
                      className="text-sm font-medium text-slate-900 hover:text-indigo-600 truncate block"
                    >
                      {e.type}
                    </Link>
                    <p className="text-xs text-slate-500 truncate">{e.summary}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge value={e.severity} />
                    <StatusBadge value={e.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Recent Audit Activity</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b">
                <th className="py-2">Action</th>
                <th className="py-2">Entity</th>
                <th className="py-2">Actor</th>
                <th className="py-2">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.recent_activity.map((a) => (
                <tr key={a.id}>
                  <td className="py-2 font-medium text-slate-800">{a.action}</td>
                  <td className="py-2 text-slate-600">{a.entity_type}</td>
                  <td className="py-2 text-slate-600">{a.actor_type}</td>
                  <td className="py-2 text-slate-500 text-xs">
                    {new Date(a.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
