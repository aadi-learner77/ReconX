import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Download, FileSpreadsheet, FileText, Printer } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  AmountCell,
  Button,
  Card,
  CitationChip,
  Drawer,
  EmptyState,
  PageCaption,
  PageSkeleton,
  StatusPill,
  Tooltip,
  toast,
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
      toast.success("Executive brief generated");
      qc.invalidateQueries({ queryKey: ["executive-briefs"] });
    },
    onError: (e: any) => {
      setErr(e.message);
      toast.error(e.message || "Failed to generate brief");
    },
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

  const citationMap = new Map<string, any>(
    (activeBrief?.citations || []).map((c: any) => [c.citation_id, c])
  );

  const openCitationDrawer = (cid: string) => {
    const found = citationMap.get(cid);
    if (found) setSelectedCitation(found);
  };

  return (
    <div className="space-y-6">
      {/* Sticky Toolbar (hidden on print) */}
      <div className="no-print sticky top-14 z-20 rounded-card border border-sand-200 bg-paper/95 backdrop-blur px-4 py-3 shadow-card flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Report Scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="px-3 py-1.5 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900"
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
              className="px-3 py-1.5 rounded-control border border-sand-200 text-xs bg-sand-50 text-ink-900 max-w-xs"
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
            <Button size="sm" loading={genMut.isPending} onClick={() => genMut.mutate()}>
              {genMut.isPending ? "Generating..." : "Generate Executive Brief"}
            </Button>
          )}
        </div>

        {activeBrief && hasPermission("reports:download") && (
          <div className="inline-flex flex-wrap items-center rounded-control border border-sand-200 bg-sand-100 p-1 gap-1">
            <button
              type="button"
              onClick={() => triggerDownload("pdf")}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] bg-ink-900 text-on-ink text-xs font-semibold"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export PDF</span>
            </button>
            <button
              type="button"
              onClick={() => triggerDownload("markdown")}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] text-xs font-semibold text-ink-900 hover:bg-paper"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Export Markdown</span>
            </button>
            <button
              type="button"
              onClick={() => triggerDownload("csv")}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] text-xs font-semibold text-ink-900 hover:bg-paper"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] text-xs font-semibold text-ink-900 hover:bg-paper"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print A4</span>
            </button>
          </div>
        )}
      </div>

      {err && (
        <Card className="no-print border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-xs max-w-[760px] mx-auto">
          {err}
        </Card>
      )}

      {isLoading ? (
        <div className="max-w-[760px] mx-auto">
          <PageSkeleton />
        </div>
      ) : !activeBrief ? (
        <div className="max-w-[760px] mx-auto">
          <EmptyState
            title="No executive briefs generated yet"
            description="Click Generate Executive Brief above to assemble a cited boardroom summary."
          />
        </div>
      ) : (
        /* Centered 760px Printed Board Paper */
        <article className="board-paper max-w-[760px] mx-auto rounded-card border border-sand-200 bg-paper p-8 md:p-12 shadow-card space-y-10">
          {/* Masthead */}
          <header className="board-section border-b border-sand-200 pb-6 space-y-4">
            <PageCaption
              project="ReconX AI / Boardroom Memorandum"
              module={`Scope / ${activeBrief.scope}`}
              index={`Checksum / ${activeBrief.content_checksum.slice(0, 12)}`}
              className="mb-2"
            />
            <h1 className="font-serif text-3xl md:text-5xl font-bold tracking-tight text-ink-900 leading-[1.08]">
              Executive Boardroom Brief
            </h1>
            <p className="text-sm text-ink-700 leading-relaxed">
              Deterministic three-way reconciliation exposure report prepared for CFO and Audit
              Committee review. Every monetary figure is computed via exact Decimal arithmetic and
              linked to verifiable PostgreSQL source records.
            </p>
            <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-ink-500 pt-1">
              <span>Report ID: {activeBrief.id}</span>
              <span>•</span>
              <span>
                Generated:{" "}
                {activeBrief.created_at
                  ? new Date(activeBrief.created_at).toLocaleString()
                  : "Current"}
              </span>
            </div>
          </header>

          {/* 01 · Pull-Quote KPIs */}
          <section className="board-section space-y-4">
            <div className="text-[11px] font-mono font-semibold uppercase tracking-[0.12em] text-ink-500">
              01 · Executive Exposure &amp; Volume Summary
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-5">
              <blockquote className="border-l-2 border-status-danger-fg pl-3.5 py-1">
                <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                  Open Exposure
                </div>
                <div className="font-mono tabular-nums text-xl md:text-2xl font-bold text-status-danger-fg mt-1">
                  {formatInrString(
                    activeBrief.exposure.open_exception_exposure,
                    activeBrief.exposure.currency
                  )}
                </div>
              </blockquote>
              <blockquote className="border-l-2 border-ink-900 pl-3.5 py-1">
                <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                  Open Exceptions
                </div>
                <div className="font-serif text-2xl md:text-3xl font-bold text-ink-900 mt-1">
                  {activeBrief.metrics.total_open_exceptions}
                </div>
              </blockquote>
              <blockquote className="border-l-2 border-sand-400 pl-3.5 py-1">
                <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                  Transactions
                </div>
                <div className="font-serif text-2xl md:text-3xl font-bold text-ink-900 mt-1">
                  {activeBrief.metrics.total_transactions_evaluated}
                </div>
              </blockquote>
              <blockquote className="border-l-2 border-sand-400 pl-3.5 py-1">
                <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                  Documents
                </div>
                <div className="font-serif text-2xl md:text-3xl font-bold text-ink-900 mt-1">
                  {activeBrief.metrics.total_documents_processed}
                </div>
              </blockquote>
            </div>
          </section>

          {/* 02 · Top Three Urgent Exceptions */}
          <section className="board-section space-y-4">
            <div className="flex items-baseline justify-between border-b border-sand-200 pb-2">
              <h2 className="font-serif text-xl font-bold text-ink-900">
                02 · Top Three Urgent Exceptions
              </h2>
              <span className="font-mono text-[11px] text-ink-500">Deterministic Ranking</span>
            </div>
            {(activeBrief.top_exceptions || []).length === 0 ? (
              <div className="text-xs text-ink-500">No open exceptions in scope.</div>
            ) : (
              <div className="space-y-4">
                {activeBrief.top_exceptions.map((t: any, idx: number) => (
                  <div
                    key={t.exception_id}
                    className="p-4 rounded-card border border-sand-200 bg-sand-50/70 text-xs space-y-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-semibold text-ink-900 text-sm">
                        <span className="font-mono text-ink-500 mr-1.5">0{idx + 1}.</span>
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
                        <AmountCell amount={t.financial_exposure} currency={t.currency} />
                      </div>
                    </div>
                    <p className="text-ink-700 leading-relaxed">
                      <strong>Why flagged ({t.rule_id}):</strong> {t.why_flagged}
                    </p>
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <Link
                        to={`/exceptions/${t.exception_id}`}
                        className="no-print text-ink-900 font-semibold underline mr-2"
                      >
                        Open Case →
                      </Link>
                      {(t.citation_ids || []).map((cid: string) => {
                        const meta = citationMap.get(cid);
                        const hoverText = meta
                          ? `${meta.source_type} · ${meta.source_display_id} (${meta.source_field}: ${meta.observed_value})`
                          : `Inspect verified evidence ${cid}`;
                        return (
                          <Tooltip key={cid} label={hoverText}>
                            <CitationChip
                              id={cid}
                              onClick={() => openCitationDrawer(cid)}
                            />
                          </Tooltip>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 03 · Footnote-Style Verified Source Citations */}
          <section className="board-section space-y-4">
            <div className="flex items-baseline justify-between border-b border-sand-200 pb-2">
              <h2 className="font-serif text-xl font-bold text-ink-900">
                03 · Verified Source Citations ({(activeBrief.citations || []).length})
              </h2>
              <span className="font-mono text-[11px] text-ink-500">
                Hover or click any footnote
              </span>
            </div>
            <ol className="space-y-2 text-xs">
              {(activeBrief.citations || []).map((c: any) => (
                <li
                  key={c.citation_id}
                  onClick={() => setSelectedCitation(c)}
                  className="flex flex-wrap items-baseline justify-between gap-2 py-1.5 border-b border-sand-200/70 cursor-pointer hover:bg-sand-50 px-2 rounded"
                >
                  <div className="flex items-center gap-2.5">
                    <Tooltip
                      label={`${c.source_type} · ${c.source_display_id} (${c.source_field}: ${c.observed_value})`}
                    >
                      <CitationChip
                        id={c.citation_id}
                        onClick={() => setSelectedCitation(c)}
                      />
                    </Tooltip>
                    <span className="text-ink-700">
                      <strong className="text-ink-900">{c.source_type}</strong> ·{" "}
                      <span className="font-mono">{c.source_display_id}</span> ·{" "}
                      <span className="text-ink-500">{c.source_field}</span>
                    </span>
                  </div>
                  <span className="font-mono font-semibold text-ink-900">
                    {c.observed_value}
                  </span>
                </li>
              ))}
            </ol>
          </section>

          {/* 04 · Policy Re-Audit Impact (if applicable) */}
          {activeBrief.policy_diff && activeBrief.policy_diff.audit_run_id && (
            <section className="board-section space-y-2 p-4 rounded-card border border-sand-200 bg-sand-50 text-xs">
              <h2 className="font-serif text-base font-bold text-ink-900">
                04 · What Changed After Policy Update (Audit {activeBrief.policy_diff.audit_run_id})
              </h2>
              <div className="font-mono text-ink-700">
                Scanned: {activeBrief.policy_diff.transactions_scanned} | New Exceptions:{" "}
                {activeBrief.policy_diff.new_exceptions} | Existing:{" "}
                {activeBrief.policy_diff.existing_exceptions} | No Longer Triggered:{" "}
                {activeBrief.policy_diff.resolved_exceptions}
              </div>
            </section>
          )}

          {/* Printed Board Paper Footer */}
          <footer className="border-t border-sand-200 pt-5 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-500">
            <span className="font-semibold text-ink-700">
              Prepared by ReconX AI · AI never approves or pays
            </span>
            <span className="font-mono">
              SHA-256 Checksum: {activeBrief.content_checksum.slice(0, 16)}
            </span>
          </footer>
        </article>
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
