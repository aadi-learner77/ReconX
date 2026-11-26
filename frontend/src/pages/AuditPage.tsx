import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { api } from "../api/client";
import { DataTable, EmptyState, PageCaption, PageSkeleton, StatusPill } from "../components/ui";

export const AuditPage: React.FC = () => {
  const [actionFilter, setActionFilter] = useState("");
  const [entityType, setEntityType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["audit", actionFilter, entityType],
    queryFn: () => api.listAudit({ action: actionFilter, entity_type: entityType }),
  });

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Governance / Audit Trail" index="Trigger-Protected Ledger" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-3xl font-bold text-ink-900">Audit Explorer</h1>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sand-100 border border-sand-200 text-[11px] font-semibold text-ink-900">
                <Lock className="w-3 h-3" aria-hidden="true" />
                <span>Immutable</span>
              </span>
            </div>
            <p className="text-sm text-ink-500 mt-1">
              Append-only audit trail protected by database triggers
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              placeholder="Filter action (e.g. CASE_DECISION_APPROVE)"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="border border-sand-200 rounded-control px-3 py-2 text-sm bg-paper text-ink-900"
            />
            <input
              placeholder="Filter entity type"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="border border-sand-200 rounded-control px-3 py-2 text-sm bg-paper text-ink-900"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <PageSkeleton />
      ) : (
        <DataTable
          rows={data?.items || []}
          rowKey={(evt: any) => evt.id}
          empty={
            <EmptyState
              title="No matching audit events"
              description="Clear your action or entity filters to inspect all audit entries."
            />
          }
          columns={[
            {
              key: "ts",
              header: "Timestamp",
              mono: true,
              render: (evt: any) => new Date(evt.timestamp).toLocaleString(),
            },
            {
              key: "actor",
              header: "Actor",
              render: (evt: any) => <StatusPill value={evt.actor_type} />,
            },
            {
              key: "action",
              header: "Action",
              render: (evt: any) => <span className="font-semibold text-ink-900">{evt.action}</span>,
            },
            {
              key: "entity",
              header: "Entity",
              mono: true,
              render: (evt: any) => `${evt.entity_type}:${evt.entity_id.slice(0, 8)}`,
            },
            {
              key: "before",
              header: "Before",
              mono: true,
              render: (evt: any) => (
                <span className="max-w-xs block truncate">
                  {evt.before_json ? JSON.stringify(evt.before_json) : "—"}
                </span>
              ),
            },
            {
              key: "after",
              header: "After",
              mono: true,
              render: (evt: any) => (
                <span className="max-w-xs block truncate">
                  {evt.after_json ? JSON.stringify(evt.after_json) : "—"}
                </span>
              ),
            },
          ]}
        />
      )}
    </div>
  );
};
