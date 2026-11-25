import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

export const ExecutiveBriefPage: React.FC = () => {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const [scope, setScope] = useState("OPEN_EXCEPTIONS");
  const [auditRunId, setAuditRunId] = useState("");
  const [selectedBriefId, setSelectedBriefId] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const { data: briefs = [], isLoading } = useQuery({
    queryKey: ["executive-briefs"],
    queryFn: api.listExecutiveBriefs,
  });
  const { data: audits = [] } = useQuery({
    queryKey: ["policy-audits"],
    queryFn: api.listPolicyAudits,
  });

  const genMut = useMutation({
    mutationFn: () =>
      api.generateExecutiveBrief({
        scope,
        policy_audit_run_id: auditRunId || null,
      }),
    onSuccess: (res) => {
      setErr(null);
      setSelectedBriefId(res.id);
      qc.invalidateQueries({ queryKey: ["executive-briefs"] });
    },
    onError: (e: any) => setErr(e.message),
  });

  const activeBrief =
    briefs.find((b: any) => b.id === selectedBriefId) || briefs[0] || null;

  const triggerDownload = async (fmt: "pdf" | "markdown" | "csv") => {
    if (!activeBrief) return;
    const blob = await api.downloadExecutiveBrief(activeBrief.id, fmt);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `executive_brief_${activeBrief.id}.${fmt === "markdown" ? "md" : fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-600 mb-1">
            <FileText className="w-3.5 h-3.5" />
            <span>Intelligence • Boardroom Reporting &amp; Citations</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Executive Boardroom Brief</h1>
          <p className="text-sm text-slate-600 mt-1">
            Generate evidence-cited CFO/auditor briefs with deterministic Decimal exposure and
            traceable provenance.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Report Scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white"
          >
            <option value="OPEN_EXCEPTIONS">Open Exceptions</option>
            <option value="LATEST_RECONCILIATION">Latest Reconciliation Run</option>
            <option value="POLICY_AUDIT_RUN">Selected Policy Re-Audit</option>
          </select>
          {audits.length > 0 && (
            <select
              aria-label="Policy Audit Run"
              value={auditRunId}
              onChange={(e) => setAuditRunId(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white max-w-xs"
            >
              <option value="">No Policy Audit Diff</option>
              {audits.map((a: any) => (
                <option key={a.id} value={a.id}>
                  Audit {a.status} ({a.new_exceptions} new) — {a.started_at.slice(0, 16)}
                </option>
              ))}
            </select>
          )}
          {hasPermission("reports:generate") && (
            <button
              type="button"
              onClick={() => genMut.mutate()}
              disabled={genMut.isPending}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
            >
              {genMut.isPending ? "Generating..." : "Generate Executive Brief"}
            </button>
          )}
        </div>
      </div>

      {err && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
          {err}
        </div>
      )}

      {isLoading ? (
        <div className="text-xs text-slate-500">Loading briefs...</div>
      ) : !activeBrief ? (
        <div className="p-8 bg-white border border-dashed border-slate-300 rounded-xl text-center text-sm text-slate-500">
          No executive briefs generated yet. Click <strong>Generate Executive Brief</strong> above.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Provenance & Export Bar */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs space-y-0.5">
              <div className="font-bold text-slate-900">
                Report ID: <span className="font-mono">{activeBrief.id}</span>
              </div>
              <div className="text-slate-500">
                Scope: {activeBrief.scope} • Checksum:{" "}
                <span className="font-mono">{activeBrief.content_checksum.slice(0, 16)}</span>
              </div>
            </div>
            {hasPermission("reports:download") && (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => triggerDownload("pdf")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export PDF</span>
                </button>
                <button
                  type="button"
                  onClick={() => triggerDownload("markdown")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Export Markdown</span>
                </button>
                <button
                  type="button"
                  onClick={() => triggerDownload("csv")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>Export CSV</span>
                </button>
              </div>
            )}
          </div>

          {/* Metrics & Financial Exposure */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <div className="text-xs text-slate-500">Documents Processed</div>
              <div className="text-xl font-bold text-slate-900">
                {activeBrief.metrics.total_documents_processed}
              </div>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <div className="text-xs text-slate-500">Transactions Evaluated</div>
              <div className="text-xl font-bold text-slate-900">
                {activeBrief.metrics.total_transactions_evaluated}
              </div>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <div className="text-xs text-slate-500">Open Exceptions</div>
              <div className="text-xl font-bold text-rose-700">
                {activeBrief.metrics.total_open_exceptions}
              </div>
            </div>
            <div className="p-4 bg-white border border-slate-200 rounded-xl">
              <div className="text-xs text-slate-500">
                Open Exposure ({activeBrief.exposure.currency})
              </div>
              <div className="text-xl font-bold text-rose-700">
                {activeBrief.exposure.open_exception_exposure}
              </div>
            </div>
          </div>

          {/* Top 3 Urgent Exceptions */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
            <h2 className="text-sm font-semibold text-slate-900">
              Top Three Urgent Exceptions (Deterministic Ranking)
            </h2>
            {(activeBrief.top_exceptions || []).length === 0 ? (
              <div className="text-xs text-slate-500">No open exceptions in scope.</div>
            ) : (
              <div className="space-y-3">
                {activeBrief.top_exceptions.map((t: any, idx: number) => (
                  <div
                    key={t.exception_id}
                    className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 text-xs space-y-1"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-bold text-slate-900">
                        #{idx + 1}{" "}
                        <Link
                          to={`/transactions/${t.transaction_id}`}
                          className="text-indigo-700 hover:underline"
                        >
                          {t.po_number}
                        </Link>{" "}
                        — {t.vendor_name}
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge value={t.severity} />
                        <span className="font-mono font-bold text-rose-700">
                          {t.currency} {t.financial_exposure}
                        </span>
                      </div>
                    </div>
                    <div className="text-slate-700">
                      <strong>Why flagged ({t.rule_id}):</strong> {t.why_flagged}
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <Link
                        to={`/exceptions/${t.exception_id}`}
                        className="text-indigo-700 font-semibold hover:underline"
                      >
                        Open Case →
                      </Link>
                      {(t.citation_ids || []).map((cid: string) => (
                        <span
                          key={cid}
                          className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-800 font-mono"
                        >
                          {cid}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Verified Evidence Citations */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
            <h2 className="text-sm font-semibold text-slate-900">
              Verified Source Citations ({(activeBrief.citations || []).length})
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Citation ID</th>
                    <th className="py-2 px-3">Source Type</th>
                    <th className="py-2 px-3">Record</th>
                    <th className="py-2 px-3">Field</th>
                    <th className="py-2 px-3">Observed Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(activeBrief.citations || []).map((c: any) => (
                    <tr key={c.citation_id}>
                      <td className="py-2 px-3 font-mono font-semibold text-indigo-700">
                        {c.citation_id}
                      </td>
                      <td className="py-2 px-3">{c.source_type}</td>
                      <td className="py-2 px-3 font-mono">{c.source_display_id}</td>
                      <td className="py-2 px-3">{c.source_field}</td>
                      <td className="py-2 px-3 font-mono">{c.observed_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Policy Diff & Historical Briefs */}
          {activeBrief.policy_diff && activeBrief.policy_diff.audit_run_id && (
            <div className="bg-white border border-indigo-200 rounded-xl p-4 shadow-sm text-xs space-y-1">
              <div className="font-bold text-indigo-900">
                What Changed After Policy Update (Audit {activeBrief.policy_diff.audit_run_id})
              </div>
              <div>
                Scanned: {activeBrief.policy_diff.transactions_scanned} | New Exceptions:{" "}
                {activeBrief.policy_diff.new_exceptions} | Existing:{" "}
                {activeBrief.policy_diff.existing_exceptions} | No Longer Triggered:{" "}
                {activeBrief.policy_diff.resolved_exceptions}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
