import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, getAccessToken } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export const TransactionsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    search: "",
    status: "",
    risk_level: "",
    vendor_id: "",
    exception_type: "",
    date_from: "",
    date_to: "",
    min_amount: "",
    max_amount: "",
  });

  const { data: vendorsData } = useQuery({
    queryKey: ["vendors-list"],
    queryFn: api.listVendors,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", filters, page],
    queryFn: () => api.listTransactions({ ...filters, page: String(page) }),
  });

  const downloadExport = async (fmt: "csv" | "pdf") => {
    const token = getAccessToken();
    const resp = await fetch(api.exportReportUrl(fmt), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reconx_report.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Transactions</h1>
          <p className="text-sm text-slate-500">
            Filter by supplier, status, risk level, exception type, date or amount
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadExport("csv")}
            className="px-3 py-1.5 border border-slate-300 bg-white rounded-lg text-xs font-medium hover:bg-slate-50"
          >
            Export CSV
          </button>
          <button
            onClick={() => downloadExport("pdf")}
            className="px-3 py-1.5 border border-slate-300 bg-white rounded-lg text-xs font-medium hover:bg-slate-50"
          >
            Export PDF
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-2 md:grid-cols-5 gap-3">
        <input
          aria-label="Search PO or vendor"
          placeholder="Search PO / Vendor / Scenario..."
          value={filters.search}
          onChange={(e) => {
            setPage(1);
            setFilters((f) => ({ ...f, search: e.target.value }));
          }}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        />
        <select
          aria-label="Supplier filter"
          value={filters.vendor_id}
          onChange={(e) => setFilters((f) => ({ ...f, vendor_id: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        >
          <option value="">All Suppliers</option>
          {(vendorsData?.items || []).map((v: any) => (
            <option key={v.id} value={v.id}>
              {v.legal_name}
            </option>
          ))}
        </select>

        <select
          aria-label="Status filter"
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="OPEN">OPEN</option>
          <option value="MATCHED">MATCHED</option>
          <option value="MATCHED_WITH_TOLERANCE">MATCHED_WITH_TOLERANCE</option>
          <option value="EXCEPTION">EXCEPTION</option>
          <option value="INCOMPLETE">INCOMPLETE</option>
          <option value="REVIEW_REQUIRED">REVIEW_REQUIRED</option>
          <option value="APPROVED">APPROVED</option>
        </select>

        <select
          aria-label="Risk level filter"
          value={filters.risk_level}
          onChange={(e) => setFilters((f) => ({ ...f, risk_level: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        >
          <option value="">All Risk Levels</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
          <option value="NONE">NONE</option>
        </select>

        <input
          placeholder="Exception type (e.g. QTY_OVER_BILLED)"
          value={filters.exception_type}
          onChange={(e) => setFilters((f) => ({ ...f, exception_type: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        />

        <input
          type="date"
          aria-label="Date from"
          value={filters.date_from}
          onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        />
        <input
          type="date"
          aria-label="Date to"
          value={filters.date_to}
          onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Min amount"
          value={filters.min_amount}
          onChange={(e) => setFilters((f) => ({ ...f, min_amount: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Max amount"
          value={filters.max_amount}
          onChange={(e) => setFilters((f) => ({ ...f, max_amount: e.target.value }))}
          className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm"
        />
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading transactions...</div>
        ) : !data?.items.length ? (
          <div className="p-6 text-sm text-slate-500 text-center">No transactions match filters.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b bg-slate-50">
                <th className="py-3 px-4">PO / Reference</th>
                <th className="py-3 px-4">Vendor</th>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Total</th>
                <th className="py-3 px-4">Outcome / Status</th>
                <th className="py-3 px-4">Risk</th>
                <th className="py-3 px-4">Scenario</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((tx) => (
                <tr key={tx.transaction_id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-4 font-medium">
                    <Link
                      to={`/transactions/${tx.transaction_id}`}
                      className="text-indigo-600 hover:underline"
                    >
                      {tx.po_number || `INV (${tx.transaction_id.slice(0, 8)})`}
                    </Link>
                  </td>
                  <td className="py-2.5 px-4 text-slate-700">{tx.vendor_name}</td>
                  <td className="py-2.5 px-4 text-slate-500">{tx.document_date}</td>
                  <td className="py-2.5 px-4 font-mono">
                    {tx.currency} {tx.total_amount}
                  </td>
                  <td className="py-2.5 px-4">
                    <StatusBadge value={tx.latest_outcome || tx.status} />
                  </td>
                  <td className="py-2.5 px-4">
                    <StatusBadge value={tx.risk_level} />
                  </td>
                  <td className="py-2.5 px-4 text-xs text-slate-500">{tx.scenario_label || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-xs text-slate-600">
          <span>
            Page {data.page} of {data.total_pages} ({data.total} total)
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1 border rounded bg-white disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 border rounded bg-white disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
