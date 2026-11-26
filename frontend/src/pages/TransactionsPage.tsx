import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, getAccessToken } from "../api/client";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  PageCaption,
  PageSkeleton,
  StatusPill,
} from "../components/ui";
import { formatInrString } from "../utils/money";

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

  const controlCls =
    "rounded-control border border-sand-200 bg-sand-50 px-3 py-2 text-sm text-ink-900 focus:border-ink-900 focus:outline-none";

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Module / Transactions Ledger" index="Three-Way Match Queue" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-ink-900">Transactions</h1>
            <p className="text-sm text-ink-500 mt-1">
              Filter by supplier, status, risk indicator level, exception type, date or amount
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => downloadExport("csv")}>
              Export CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => downloadExport("pdf")}>
              Export PDF
            </Button>
          </div>
        </div>
      </div>

      <Card className="grid grid-cols-2 md:grid-cols-5 gap-3 p-4">
        <input
          aria-label="Search PO or vendor"
          placeholder="Search PO / Vendor / Scenario..."
          value={filters.search}
          onChange={(e) => {
            setPage(1);
            setFilters((f) => ({ ...f, search: e.target.value }));
          }}
          className={controlCls}
        />
        <select
          aria-label="Supplier filter"
          value={filters.vendor_id}
          onChange={(e) => setFilters((f) => ({ ...f, vendor_id: e.target.value }))}
          className={controlCls}
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
          className={controlCls}
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
          className={controlCls}
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
          className={controlCls}
        />

        <input
          type="date"
          aria-label="Date from"
          value={filters.date_from}
          onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
          className={controlCls}
        />
        <input
          type="date"
          aria-label="Date to"
          value={filters.date_to}
          onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
          className={controlCls}
        />
        <input
          type="number"
          placeholder="Min amount"
          value={filters.min_amount}
          onChange={(e) => setFilters((f) => ({ ...f, min_amount: e.target.value }))}
          className={controlCls}
        />
        <input
          type="number"
          placeholder="Max amount"
          value={filters.max_amount}
          onChange={(e) => setFilters((f) => ({ ...f, max_amount: e.target.value }))}
          className={controlCls}
        />
      </Card>

      {isLoading ? (
        <PageSkeleton />
      ) : (
        <DataTable
          rows={data?.items || []}
          rowKey={(tx) => tx.transaction_id}
          empty={
            <EmptyState
              title="No matching transactions"
              description="Adjust your filters to view purchase orders and invoices."
            />
          }
          columns={[
            {
              key: "po",
              header: "PO / Reference",
              mono: true,
              render: (tx) => (
                <Link
                  to={`/transactions/${tx.transaction_id}`}
                  className="font-semibold text-ink-900 underline"
                >
                  {tx.po_number || `INV (${tx.transaction_id.slice(0, 8)})`}
                </Link>
              ),
            },
            { key: "vendor", header: "Vendor", render: (tx) => tx.vendor_name },
            { key: "date", header: "Date", mono: true, render: (tx) => tx.document_date },
            {
              key: "total",
              header: "Total",
              align: "right",
              mono: true,
              render: (tx) => formatInrString(tx.total_amount, tx.currency),
            },
            {
              key: "outcome",
              header: "Outcome / Status",
              render: (tx) => <StatusPill value={tx.latest_outcome || tx.status} />,
            },
            {
              key: "risk",
              header: "Risk Indicator",
              render: (tx) => <StatusPill value={tx.risk_level} />,
            },
            {
              key: "scenario",
              header: "Scenario",
              mono: true,
              render: (tx) => tx.scenario_label || "—",
            },
          ]}
        />
      )}

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-xs text-ink-500">
          <span className="font-mono">
            Page {data.page} of {data.total_pages} ({data.total} total)
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
