import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Button, Card, DataTable, Input, PageCaption, StatusPill } from "../components/ui";

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
    <div className="space-y-8">
      <div>
        <PageCaption module="Governance / System Configuration" index="Tolerances, RBAC & Jobs" />
        <h1 className="font-display text-3xl font-bold text-ink-900">Admin Settings</h1>
        <p className="text-sm text-ink-500 mt-1">
          Versioned tolerances, workflow policies, users &amp; background jobs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="space-y-4">
          <h2 className="font-display text-lg font-bold text-ink-900">
            Active Tolerance Rules ({tolerances.length})
          </h2>
          <div className="flex flex-wrap gap-3 items-end">
            <Input
              label="Price % Tolerance"
              value={pricePct}
              onChange={(e) => setPricePct(e.target.value)}
              className="w-36 font-mono"
            />
            <Input
              label="Qty Abs Tolerance"
              value={qtyAbs}
              onChange={(e) => setQtyAbs(e.target.value)}
              className="w-36 font-mono"
            />
            <Button onClick={() => saveTol.mutate()} disabled={saveTol.isPending}>
              Update Org Default
            </Button>
          </div>
          <ul className="text-xs space-y-1.5 text-ink-700 pt-2 border-t border-sand-200">
            {tolerances.map((t: any) => (
              <li key={t.id} className="font-mono">
                v{t.version}: price_pct={t.price_pct_tolerance}, qty_abs={t.qty_abs_tolerance},
                tax_abs={t.tax_abs_tolerance}
              </li>
            ))}
          </ul>
        </Card>

        <Card className="space-y-3">
          <h2 className="font-display text-lg font-bold text-ink-900">
            Organization Config (v{configData?.version || 1})
          </h2>
          <pre className="text-xs font-mono bg-sand-50 border border-sand-200 rounded-control p-3.5 overflow-auto max-h-48 text-ink-900">
            {JSON.stringify(configData?.config_json || {}, null, 2)}
          </pre>
        </Card>
      </div>

      <div className="space-y-3">
        <h2 className="font-display text-xl font-bold text-ink-900">Users &amp; Roles</h2>
        <DataTable
          rows={usersData?.items || []}
          rowKey={(u: any) => u.id}
          columns={[
            { key: "name", header: "Name", render: (u: any) => <span className="font-semibold">{u.full_name}</span> },
            { key: "email", header: "Email", mono: true, render: (u: any) => u.email },
            { key: "roles", header: "Roles", mono: true, render: (u: any) => u.roles.join(", ") },
            { key: "status", header: "Status", render: (u: any) => <StatusPill value={u.status} /> },
          ]}
        />
      </div>

      <div className="space-y-3">
        <h2 className="font-display text-xl font-bold text-ink-900">Background Document Jobs</h2>
        <DataTable
          rows={jobsData?.items || []}
          rowKey={(j: any) => j.job_id}
          columns={[
            { key: "id", header: "Job ID", mono: true, render: (j: any) => j.job_id.slice(0, 8) },
            { key: "status", header: "Status", render: (j: any) => <StatusPill value={j.status} /> },
            { key: "attempts", header: "Attempts", mono: true, render: (j: any) => j.attempts },
            { key: "err", header: "Last Error", render: (j: any) => j.last_error || "—" },
            {
              key: "action",
              header: "Action",
              render: (j: any) =>
                j.status === "FAILED" ? (
                  <Button variant="outline" size="sm" onClick={() => retryMut.mutate(j.job_id)}>
                    Retry
                  </Button>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </div>
    </div>
  );
};
