import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export const AdminPage: React.FC = () => {
  const qc = useQueryClient();
  const [pricePct, setPricePct] = useState("0.02");
  const [qtyAbs, setQtyAbs] = useState("0");

  const { data: configData } = useQuery({ queryKey: ["admin-config"], queryFn: api.getConfig });
  const { data: tolerances = [] } = useQuery({
    queryKey: ["admin-tolerances"],
    queryFn: api.listTolerances,
  });
  const { data: jobsData } = useQuery({ queryKey: ["admin-jobs"], queryFn: api.listJobs });
  const { data: usersData } = useQuery({ queryKey: ["admin-users"], queryFn: api.listUsers });

  const saveTol = useMutation({
    mutationFn: () =>
      api.upsertTolerance({
        price_abs_tolerance: "0",
        price_pct_tolerance: pricePct,
        qty_abs_tolerance: qtyAbs,
        qty_pct_tolerance: "0",
        tax_abs_tolerance: "1.00",
        allow_partial_billing: true,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-tolerances"] }),
  });

  const retryMut = useMutation({
    mutationFn: (jobId: string) => api.retryJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-jobs"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Admin Settings</h1>
        <p className="text-sm text-slate-500">
          Versioned tolerances, workflow policies, users & background jobs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">
            Active Tolerance Rules ({tolerances.length})
          </h2>
          <div className="flex gap-2 items-end">
            <div>
              <label className="block text-xs text-slate-500">Price % Tolerance</label>
              <input
                value={pricePct}
                onChange={(e) => setPricePct(e.target.value)}
                className="border border-slate-300 rounded px-2.5 py-1.5 text-sm w-32"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500">Qty Abs Tolerance</label>
              <input
                value={qtyAbs}
                onChange={(e) => setQtyAbs(e.target.value)}
                className="border border-slate-300 rounded px-2.5 py-1.5 text-sm w-32"
              />
            </div>
            <button
              onClick={() => saveTol.mutate()}
              className="px-3.5 py-1.5 bg-indigo-600 text-white text-sm rounded-lg"
            >
              Update Org Default
            </button>
          </div>
          <ul className="text-xs space-y-1 text-slate-600 pt-2">
            {tolerances.map((t: any) => (
              <li key={t.id} className="font-mono">
                v{t.version}: price_pct={t.price_pct_tolerance}, qty_abs={t.qty_abs_tolerance}, tax_abs=
                {t.tax_abs_tolerance}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
          <h2 className="text-sm font-semibold text-slate-900">
            Organization Config (v{configData?.version || 1})
          </h2>
          <pre className="text-xs bg-slate-50 border rounded-lg p-3 overflow-auto max-h-48">
            {JSON.stringify(configData?.config_json || {}, null, 2)}
          </pre>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">Users & Roles</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b">
                <th className="py-2">Name</th>
                <th className="py-2">Email</th>
                <th className="py-2">Roles</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(usersData?.items || []).map((u: any) => (
                <tr key={u.id}>
                  <td className="py-2 font-medium">{u.full_name}</td>
                  <td className="py-2 text-slate-600">{u.email}</td>
                  <td className="py-2 font-mono text-xs">{u.roles.join(", ")}</td>
                  <td className="py-2">
                    <StatusBadge value={u.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">Background Document Jobs</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2">Job ID</th>
                <th className="py-2">Status</th>
                <th className="py-2">Attempts</th>
                <th className="py-2">Last Error</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(jobsData?.items || []).map((j: any) => (
                <tr key={j.job_id}>
                  <td className="py-2 font-mono">{j.job_id.slice(0, 8)}</td>
                  <td className="py-2">
                    <StatusBadge value={j.status} />
                  </td>
                  <td className="py-2">
                    {j.attempts}/{j.max_attempts}
                  </td>
                  <td className="py-2 text-rose-700">{j.last_error || "—"}</td>
                  <td className="py-2">
                    {j.status === "FAILED" && (
                      <button
                        onClick={() => retryMut.mutate(j.job_id)}
                        className="px-2 py-1 bg-indigo-600 text-white rounded"
                      >
                        Retry
                      </button>
                    )}
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
