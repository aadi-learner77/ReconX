import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { DataTable, EmptyState, PageCaption, PageSkeleton, StatusPill } from "../components/ui";

export const ExceptionsPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["exceptions", statusFilter],
    queryFn: () => api.listExceptions(statusFilter),
  });

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Module / Exception Queue" index="Maker-Checker Governance" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-ink-900">Exceptions</h1>
            <p className="text-sm text-ink-500 mt-1">
              Discrepancies, missing records &amp; review-required cases
            </p>
          </div>
          <select
            aria-label="Filter exception status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-control border border-sand-200 bg-paper px-3 py-2 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="IN_REVIEW">IN_REVIEW</option>
            <option value="INFO_REQUESTED">INFO_REQUESTED</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <PageSkeleton />
      ) : (
        <DataTable
          rows={data?.items || []}
          rowKey={(c) => c.id}
          empty={
            <EmptyState
              title="No exception cases found"
              description="All reconciled transactions are currently within tolerance."
            />
          }
          columns={[
            {
              key: "type",
              header: "Type",
              render: (c) => (
                <Link to={`/exceptions/${c.id}`} className="font-semibold text-ink-900 underline">
                  {c.type}
                </Link>
              ),
            },
            { key: "rule", header: "Rule", mono: true, render: (c) => c.rule_id },
            { key: "severity", header: "Severity", render: (c) => <StatusPill value={c.severity} /> },
            { key: "status", header: "Status", render: (c) => <StatusPill value={c.status} /> },
            {
              key: "summary",
              header: "Summary",
              render: (c) => <span className="text-ink-700 max-w-md block truncate">{c.summary}</span>,
            },
          ]}
        />
      )}
    </div>
  );
};
