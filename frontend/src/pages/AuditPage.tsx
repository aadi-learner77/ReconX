import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export const AuditPage: React.FC = () => {
  const [actionFilter, setActionFilter] = useState("");
  const [entityType, setEntityType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["audit", actionFilter, entityType],
    queryFn: () => api.listAudit({ action: actionFilter, entity_type: entityType }),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Audit Explorer</h1>
          <p className="text-sm text-slate-500">
            Append-only audit trail protected by database triggers
          </p>
        </div>
        <div className="flex gap-2">
          <input
            placeholder="Filter action (e.g. CASE_DECISION_APPROVE)"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white"
          />
          <input
            placeholder="Filter entity type"
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white"
          />
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading audit events...</div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500 border-b bg-slate-50">
                <th className="py-3 px-3">Timestamp</th>
                <th className="py-3 px-3">Actor</th>
                <th className="py-3 px-3">Action</th>
                <th className="py-3 px-3">Entity</th>
                <th className="py-3 px-3">Before</th>
                <th className="py-3 px-3">After</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(data?.items || []).map((evt: any) => (
                <tr key={evt.id}>
                  <td className="py-2 px-3 whitespace-nowrap text-slate-500">
                    {new Date(evt.timestamp).toLocaleString()}
                  </td>
                  <td className="py-2 px-3 font-mono">{evt.actor_type}</td>
                  <td className="py-2 px-3 font-semibold text-slate-800">{evt.action}</td>
                  <td className="py-2 px-3 font-mono">
                    {evt.entity_type}:{evt.entity_id.slice(0, 8)}
                  </td>
                  <td className="py-2 px-3 font-mono max-w-xs truncate">
                    {evt.before_json ? JSON.stringify(evt.before_json) : "—"}
                  </td>
                  <td className="py-2 px-3 font-mono max-w-xs truncate">
                    {evt.after_json ? JSON.stringify(evt.after_json) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
