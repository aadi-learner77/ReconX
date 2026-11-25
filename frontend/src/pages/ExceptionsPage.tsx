import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export const ExceptionsPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["exceptions", statusFilter],
    queryFn: () => api.listExceptions(statusFilter),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Exceptions</h1>
          <p className="text-sm text-slate-500">
            Discrepancies, missing records & review-required cases
          </p>
        </div>
        <select
          aria-label="Filter exception status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white"
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

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        {isLoading ? (
          <div className="p-6 text-sm text-slate-500">Loading exceptions...</div>
        ) : !data?.items.length ? (
          <div className="p-6 text-sm text-slate-500 text-center">No exception cases found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b bg-slate-50">
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Rule</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-4 font-medium">
                    <Link to={`/exceptions/${c.id}`} className="text-indigo-600 hover:underline">
                      {c.type}
                    </Link>
                  </td>
                  <td className="py-2.5 px-4 font-mono text-xs">{c.rule_id}</td>
                  <td className="py-2.5 px-4">
                    <StatusBadge value={c.severity} />
                  </td>
                  <td className="py-2.5 px-4">
                    <StatusBadge value={c.status} />
                  </td>
                  <td className="py-2.5 px-4 text-slate-600 max-w-md truncate">{c.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
