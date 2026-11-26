import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ShieldAlert, Sparkles } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, PageCaption, PageSkeleton, StatusPill, Toast } from "../components/ui";

export const ExceptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user, hasPermission } = useAuth();
  const qc = useQueryClient();

  const [commentText, setCommentText] = useState("");
  const [isClarification, setIsClarification] = useState(false);
  const [decisionType, setDecisionType] = useState<"APPROVE" | "REJECT" | "REQUEST_INFO" | "ESCALATE">("APPROVE");
  const [rationale, setRationale] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const { data: exc, isLoading } = useQuery({
    queryKey: ["exception", id],
    queryFn: () => api.getException(id!),
    enabled: Boolean(id),
  });

  const { data: usersData } = useQuery({
    queryKey: ["admin-users"],
    queryFn: api.listUsers,
    enabled: hasPermission("admin:users:read"),
  });

  const investigateMut = useMutation({
    mutationFn: () => api.startInvestigation(id!),
    onSuccess: () => {
      setActionMsg("Investigation completed with evidence citations.");
      qc.invalidateQueries({ queryKey: ["exception", id] });
    },
  });

  const assignMut = useMutation({
    mutationFn: (ownerId: string) => api.assignException(id!, ownerId),
    onSuccess: () => {
      setActionMsg("Case owner updated.");
      qc.invalidateQueries({ queryKey: ["exception", id] });
    },
  });

  const commentMut = useMutation({
    mutationFn: () => api.addComment(id!, commentText, isClarification),
    onSuccess: () => {
      setCommentText("");
      qc.invalidateQueries({ queryKey: ["exception", id] });
    },
  });

  const decideMut = useMutation({
    mutationFn: () => api.decideException(id!, decisionType, rationale, exc!.version),
    onSuccess: (res) => {
      setConfirmOpen(false);
      setRationale("");
      setActionMsg(`Workflow decision recorded: ${res.status} (Audit ${res.audit_event_id.slice(0, 8)}).`);
      qc.invalidateQueries({ queryKey: ["exception", id] });
    },
  });

  if (isLoading || !exc) return <PageSkeleton />;

  const latestInv = exc.investigations[0]?.structured_output;
  const errMsg = ((decideMut.error || investigateMut.error) as Error | undefined)?.message;
  const isRoleNotice = Boolean(errMsg && (errMsg.includes("403") || errMsg.toLowerCase().includes("permission") || errMsg.toLowerCase().includes("maker")));

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Module / Exception & Maker-Checker" index={`Case ${exc.id.slice(0, 8)}`} />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-3xl font-bold text-ink-900">{exc.type}</h1>
              <StatusPill value={exc.severity} />
              <StatusPill value={exc.status} />
            </div>
            <p className="text-sm text-ink-500 mt-1">
              Rule <span className="font-mono">{exc.rule_id}</span> • Version{" "}
              <span className="font-mono">{exc.version}</span> •{" "}
              <Link to={`/transactions/${exc.transaction_id}`} className="text-ink-900 underline font-medium">
                View Transaction Bundle
              </Link>
            </p>
          </div>
          <div className="flex gap-2">
            {hasPermission("investigations:run") && (
              <Button onClick={() => investigateMut.mutate()} disabled={investigateMut.isPending}>
                <Sparkles className="w-4 h-4" />
                <span>{investigateMut.isPending ? "Investigating..." : "Run Investigation Agent"}</span>
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Maker-Checker Governance Banner */}
      <Card variant="subtle" className="py-3.5 px-5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 font-semibold text-ink-900">
          <ShieldAlert className="w-4 h-4" />
          <span>Maker-Checker Governance</span>
        </div>
        <div className="font-mono text-ink-700">
          Maker: System / Operator • Checker: {user?.full_name || "Approver"} (
          {user?.roles.join(", ")})
        </div>
      </Card>

      {actionMsg && <Toast message={actionMsg} tone="success" onDismiss={() => setActionMsg(null)} />}

      {errMsg && (
        <div
          className={
            isRoleNotice
              ? "p-4 rounded-card bg-sand-100 border border-sand-400 text-sm text-ink-900"
              : "p-4 rounded-card bg-status-danger-bg border border-status-danger-fg/30 text-sm text-status-danger-fg"
          }
        >
          {isRoleNotice ? `Role Notice: ${errMsg}` : errMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-6">
          <Card className="space-y-3">
            <h2 className="font-display text-lg font-bold text-ink-900">Discrepancy Summary</h2>
            <p className="text-sm text-ink-700">{exc.summary}</p>
            <div className="grid grid-cols-2 gap-3 text-xs bg-sand-50 p-3.5 rounded-control border border-sand-200">
              {Object.entries(exc.values || {}).map(([k, v]) => (
                <div key={k}>
                  <span className="text-ink-500">{k}: </span>
                  <span className="font-mono font-semibold text-ink-900">{String(v)}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Investigation Workspace */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-display text-lg font-bold text-ink-900">Investigation Findings</h2>
              {latestInv && (
                <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-sand-100 text-ink-900 border border-sand-200">
                  {exc.investigations[0].model_provider} • {Math.round(exc.investigations[0].confidence * 100)}%
                </span>
              )}
            </div>

            {!latestInv ? (
              <div className="text-sm text-ink-500">
                No investigation run yet. Click &ldquo;Run Investigation Agent&rdquo; to gather grounded evidence.
              </div>
            ) : (
              <div className="space-y-4 text-sm">
                <div className="p-3.5 rounded-control bg-sand-50 border border-sand-200 text-ink-900">
                  {latestInv.summary}
                </div>

                <div>
                  <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
                    Verified Facts
                  </div>
                  <ul className="list-disc pl-5 text-ink-700 mt-1.5 space-y-1">
                    {(latestInv.facts || []).map((f: string, idx: number) => (
                      <li key={idx}>{f}</li>
                    ))}
                  </ul>
                </div>

                {(latestInv.missing_information || []).length > 0 && (
                  <div>
                    <div className="text-[11px] font-semibold text-status-warning-fg uppercase tracking-[0.08em]">
                      Unknown / Missing Information
                    </div>
                    <ul className="list-disc pl-5 text-status-warning-fg mt-1.5 space-y-1">
                      {latestInv.missing_information.map((m: string, idx: number) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(latestInv.hypotheses || []).length > 0 && (
                  <div>
                    <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
                      Inferred Hypotheses (Unverified)
                    </div>
                    <ul className="list-disc pl-5 text-ink-700 mt-1.5 space-y-1">
                      {latestInv.hypotheses.map((h: string, idx: number) => (
                        <li key={idx}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
                    Evidence References
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {(latestInv.evidence_refs || []).map((ref: any, idx: number) => (
                      <span
                        key={idx}
                        className="text-xs px-2.5 py-1 rounded-full bg-sand-100 border border-sand-200 font-mono text-ink-900"
                      >
                        {ref.type}:{ref.label || ref.id}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3.5 rounded-control bg-status-success-bg border border-status-success-fg/20 text-xs text-status-success-fg space-y-1">
                  <div>
                    <strong>Recommended Next Action:</strong> {latestInv.recommended_action}
                  </div>
                  <div className="text-[11px] font-semibold font-mono">
                    {latestInv.actual_provider === "gemini" && !latestInv.fallback_used
                      ? "Generated with Google Gemini"
                      : latestInv.fallback_used
                        ? "Mock fallback used — not Gemini-generated."
                        : `Provider: ${latestInv.actual_provider || exc.investigations[0]?.model_provider || "mock"}`}
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Comments */}
          <Card className="space-y-4">
            <h2 className="font-display text-lg font-bold text-ink-900">
              Case Discussion &amp; Clarifications
            </h2>
            <ul className="space-y-2">
              {exc.comments.map((cm) => (
                <li key={cm.id} className="p-3 rounded-control bg-sand-50 border border-sand-200 text-sm">
                  <div className="text-xs font-mono text-ink-500">
                    {new Date(cm.created_at).toLocaleString()}
                    {cm.is_clarification_request ? " • Clarification Request" : ""}
                  </div>
                  <div className="mt-1 text-ink-900 whitespace-pre-wrap">{cm.body}</div>
                </li>
              ))}
            </ul>
            {hasPermission("exceptions:comment") && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (commentText.trim()) commentMut.mutate();
                }}
                className="space-y-2.5"
              >
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Add review note or clarification request..."
                  className="w-full border border-sand-200 bg-sand-50 rounded-control p-2.5 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
                  rows={2}
                />
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-xs text-ink-700">
                    <input
                      type="checkbox"
                      checked={isClarification}
                      onChange={(e) => setIsClarification(e.target.checked)}
                    />
                    Mark as clarification request
                  </label>
                  <Button type="submit" variant="secondary" size="sm">
                    Post Note
                  </Button>
                </div>
              </form>
            )}
          </Card>
        </div>

        {/* Right rail: Workflow Decision & Assignment */}
        <div className="lg:col-span-5 space-y-6">
          {hasPermission("exceptions:manage") && usersData?.items && (
            <Card className="space-y-2.5">
              <h2 className="font-display text-base font-bold text-ink-900">Assign Case Owner</h2>
              <select
                aria-label="Assign owner"
                value={exc.owner_id || ""}
                onChange={(e) => e.target.value && assignMut.mutate(e.target.value)}
                className="w-full border border-sand-200 bg-sand-50 rounded-control px-3 py-2 text-sm text-ink-900"
              >
                <option value="">Unassigned</option>
                {usersData.items.map((u: any) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.roles.join(", ")})
                  </option>
                ))}
              </select>
            </Card>
          )}

          <Card className="space-y-4">
            <div>
              <h2 className="font-display text-lg font-bold text-ink-900">Workflow Decision</h2>
              <p className="text-xs text-ink-500 mt-0.5">
                Approval records a workflow decision only — never executes a bank payment.
              </p>
            </div>

            <div className="space-y-3">
              <select
                aria-label="Decision action"
                value={decisionType}
                onChange={(e) => setDecisionType(e.target.value as any)}
                className="w-full border border-sand-200 bg-sand-50 rounded-control px-3 py-2 text-sm text-ink-900"
              >
                <option value="APPROVE">APPROVE (Workflow)</option>
                <option value="REJECT">REJECT</option>
                <option value="REQUEST_INFO">REQUEST_INFO</option>
                <option value="ESCALATE">ESCALATE</option>
              </select>

              <textarea
                aria-label="Decision rationale"
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Mandatory decision rationale (min 3 characters)..."
                rows={3}
                className="w-full border border-sand-200 bg-sand-50 rounded-control p-2.5 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
              />

              <Button
                disabled={rationale.trim().length < 3}
                onClick={() => setConfirmOpen(true)}
                className="w-full"
              >
                Submit Decision
              </Button>
              {rationale.trim().length < 3 && (
                <p className="text-[11px] text-ink-500">
                  Enter at least 3 characters of rationale to enable workflow decision.
                </p>
              )}
            </div>

            {confirmOpen && (
              <div className="p-3.5 rounded-control bg-status-warning-bg border border-status-warning-fg/30 space-y-2.5 text-xs">
                <div className="font-semibold text-status-warning-fg">
                  Confirm {decisionType} on case {exc.id.slice(0, 8)}?
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => decideMut.mutate()}
                    disabled={decideMut.isPending}
                  >
                    Confirm
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setConfirmOpen(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {exc.approvals.length > 0 && (
              <div className="pt-3 border-t border-sand-200 space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                  Decision History
                </div>
                {exc.approvals.map((ap) => (
                  <div key={ap.id} className="text-xs p-3 rounded-control bg-sand-50 border border-sand-200">
                    <div className="font-semibold text-ink-900">{ap.decision}</div>
                    <div className="text-ink-700 mt-0.5">{ap.rationale}</div>
                    <div className="text-ink-500 font-mono mt-1">
                      {new Date(ap.decided_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
