import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Button,
  Card,
  Drawer,
  EmptyState,
  PageCaption,
  PageSkeleton,
  Stat,
  StatusPill,
} from "../components/ui";
import { formatInrString } from "../utils/money";

export const ExecutiveBriefPage: React.FC = () => {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const [scope, setScope] = useState("OPEN_EXCEPTIONS");
  const [auditRunId, setAuditRunId] = useState("");
  const [selectedBriefId, setSelectedBriefId] = useState<string>("");
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);
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

  const openCitationDrawer = (cid: string) => {
    const found = (activeBrief?.citations || []).find((c: any) => c.citation_id === cid);
    if (found) setSelectedCitation(found);
  };

  return (
    <div className="space-y-8">
      <Card variant="hero">
        <PageCaption
          module="Intelligence / Boardroom Reporting"
          index="Deterministic Decimal Brief"
        />
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="font-display text-3xl md:text-5xl font-bold text-ink-900">
              Executive Boardroom Brief
            </h1>
            <p className="text-sm text-ink-700 mt-2 max-w-2xl">
              Generate evidence-cited CFO and auditor briefs with quantified Decimal exposure and
              traceable database provenance.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <select
              aria-label="Report Scope"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-paper text-ink-900"
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
                className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-paper text-ink-900 max-w-xs"
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
              <Button onClick={() => genMut.mutate()} disabled={genMut.isPending}>
                {genMut.isPending ? "Generating..." : "Generate Executive Brief"}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {err && (
        <Card className="border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-xs">
          {err}
        </Card>
      )}

      {isLoading ? (
        <PageSkeleton />
      ) : !activeBrief ? (
        <EmptyState
          title="No executive briefs generated yet"
          description="Click Generate Executive Brief above to assemble a cited boardroom summary."
        />
      ) : (
        <div className="space-y-8">
          {/* Editorial Reading Column */}
          <div className="max-w-[760px] space-y-6">
            <Card className="flex flex-wrap items-center justify-between gap-4">
              <div className="text-xs space-y-1">
                <div className="font-semibold text-ink-900">
                  Report ID: <span className="font-mono">{activeBrief.id}</span>
                </div>
                <div className="text-ink-500 font-mono">
                  Scope: {activeBrief.scope} • Checksum: {activeBrief.content_checksum.slice(0, 16)}
                </div>
              </div>
              {hasPermission("reports:download") && (
                <div className="inline-flex rounded-control border border-sand-200 bg-sand-100 p-1 gap-1">
                  <button
                    type="button"
                    onClick={() => triggerDownload("pdf")}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[7px] bg-ink-900 text-on-ink text-xs font-semibold"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export PDF</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => triggerDownload("markdown")}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[7px] text-xs font-semibold text-ink-900 hover:bg-paper"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Export Markdown</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => triggerDownload("csv")}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[7px] text-xs font-semibold text-ink-900 hover:bg-paper"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    <span>Export CSV</span>
                  </button>
                </div>
              )}
            </Card>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Stat label="Documents Processed" value={activeBrief.metrics.total_documents_processed} />
              <Stat label="Transactions Evaluated" value={activeBrief.metrics.total_transactions_evaluated} />
              <Stat label="Open Exceptions" value={activeBrief.metrics.total_open_exceptions} tone="danger" />
              <Stat
                label={`Open Exposure (${activeBrief.exposure.currency})`}
                value={formatInrString(activeBrief.exposure.open_exception_exposure, activeBrief.exposure.currency)}
                mono
                tone="danger"
              />
            </div>

            <Card className="space-y-4">
              <h2 className="font-display text-xl font-bold text-ink-900">
                Top Three Urgent Exceptions (Deterministic Ranking)
              </h2>
              {(activeBrief.top_exceptions || []).length === 0 ? (
                <div className="text-xs text-ink-500">No open exceptions in scope.</div>
              ) : (
                <div className="space-y-3">
                  {activeBrief.top_exceptions.map((t: any, idx: number) => (
                    <div
                      key={t.exception_id}
                      className="p-4 rounded-card border border-sand-200 bg-sand-50 text-xs space-y-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-bold text-ink-900">
                          #{idx + 1}{" "}
                          <Link
                            to={`/transactions/${t.transaction_id}`}
                            className="font-mono underline"
                          >
                            {t.po_number}
                          </Link>{" "}
                          — {t.vendor_name}
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusPill value={t.severity} />
                          <span className="font-mono font-bold text-status-danger-fg">
                            {formatInrString(t.financial_exposure, t.currency)}
                          </span>
                        </div>
                      </div>
                      <div className="text-ink-700">
                        <strong>Why flagged ({t.rule_id}):</strong> {t.why_flagged}
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <Link
                          to={`/exceptions/${t.exception_id}`}
                          className="text-ink-900 font-semibold underline mr-2"
                        >
                          Open Case →
                        </Link>
                        {(t.citation_ids || []).map((cid: string) => (
                          <button
                            key={cid}
                            type="button"
                            onClick={() => openCitationDrawer(cid)}
                            className="px-2 py-0.5 rounded-full bg-paper border border-sand-200 hover:border-ink-900 font-mono text-ink-900"
                          >
                            [{cid}]
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Verified Evidence Citations Table */}
          <Card className="space-y-3">
            <h2 className="font-display text-lg font-bold text-ink-900">
              Verified Source Citations ({(activeBrief.citations || []).length})
            </h2>
            <div className="overflow-x-auto rounded-card border border-sand-200">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-sand-100 text-ink-500 border-b border-sand-200">
                  <tr>
                    <th scope="col" className="py-2.5 px-3">Citation ID</th>
                    <th scope="col" className="py-2.5 px-3">Source Type</th>
                    <th scope="col" className="py-2.5 px-3">Record</th>
                    <th scope="col" className="py-2.5 px-3">Field</th>
                    <th scope="col" className="py-2.5 px-3">Observed Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sand-200">
                  {(activeBrief.citations || []).map((c: any) => (
                    <tr
                      key={c.citation_id}
                      onClick={() => setSelectedCitation(c)}
                      className="cursor-pointer hover:bg-sand-50"
                    >
                      <td className="py-2.5 px-3 font-semibold text-ink-900 underline">
                        {c.citation_id}
                      </td>
                      <td className="py-2.5 px-3 font-sans">{c.source_type}</td>
                      <td className="py-2.5 px-3">{c.source_display_id}</td>
                      <td className="py-2.5 px-3 font-sans">{c.source_field}</td>
                      <td className="py-2.5 px-3">{c.observed_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {activeBrief.policy_diff && activeBrief.policy_diff.audit_run_id && (
            <Card variant="subtle" className="text-xs space-y-1">
              <div className="font-bold text-ink-900">
                What Changed After Policy Update (Audit {activeBrief.policy_diff.audit_run_id})
              </div>
              <div className="font-mono text-ink-700">
                Scanned: {activeBrief.policy_diff.transactions_scanned} | New Exceptions:{" "}
                {activeBrief.policy_diff.new_exceptions} | Existing:{" "}
                {activeBrief.policy_diff.existing_exceptions} | No Longer Triggered:{" "}
                {activeBrief.policy_diff.resolved_exceptions}
              </div>
            </Card>
          )}
        </div>
      )}

      <Drawer
        open={Boolean(selectedCitation)}
        onClose={() => setSelectedCitation(null)}
        title={selectedCitation ? `Citation ${selectedCitation.citation_id}` : "Citation"}
        subtitle="Authoritative PostgreSQL Evidence Record"
      >
        {selectedCitation && (
          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200 space-y-1.5">
              <div>
                <span className="text-ink-500">Source Type:</span>{" "}
                <strong className="text-ink-900">{selectedCitation.source_type}</strong>
              </div>
              <div>
                <span className="text-ink-500">Record:</span>{" "}
                <span className="font-mono font-semibold text-ink-900">
                  {selectedCitation.source_display_id}
                </span>
              </div>
              <div>
                <span className="text-ink-500">Field:</span>{" "}
                <span className="font-mono text-ink-900">{selectedCitation.source_field}</span>
              </div>
              <div>
                <span className="text-ink-500">Observed Value:</span>{" "}
                <span className="font-mono font-bold text-ink-900">
                  {selectedCitation.observed_value}
                </span>
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
