import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

export const ExceptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuth();
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

  if (isLoading || !exc) return <div className="text-sm text-slate-500">Loading case...</div>;

  const latestInv = exc.investigations[0]?.structured_output;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">{exc.type}</h1>
            <StatusBadge value={exc.severity} />
            <StatusBadge value={exc.status} />
          </div>
          <p className="text-sm text-slate-500 mt-0.5">
            Rule {exc.rule_id} • Version {exc.version} •{" "}
            <Link to={`/transactions/${exc.transaction_id}`} className="text-indigo-600 hover:underline">
              View Transaction Bundle
            </Link>
          </p>
        </div>
        <div className="flex gap-2">
          {hasPermission("investigations:run") && (
            <button
              onClick={() => investigateMut.mutate()}
              disabled={investigateMut.isPending}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
            >
              {investigateMut.isPending ? "Investigating..." : "Run Investigation Agent"}
            </button>
          )}
        </div>
      </div>

      {actionMsg && (
        <div className="p-3 rounded-lg bg-indigo-50 border border-indigo-200 text-sm text-indigo-900">
          {actionMsg}
        </div>
      )}
      {(decideMut.isError || investigateMut.isError) && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
          {((decideMut.error || investigateMut.error) as Error).message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <h2 className="text-sm font-semibold text-slate-900">Discrepancy Summary</h2>
            <p className="text-sm text-slate-700">{exc.summary}</p>
            <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-3 rounded-lg border">
              {Object.entries(exc.values || {}).map(([k, v]) => (
                <div key={k}>
                  <span className="text-slate-500">{k}: </span>
                  <span className="font-mono font-semibold text-slate-900">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Investigation Workspace */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">Investigation Findings</h2>
              {latestInv && (
                <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                  AI-assisted • Provider: {exc.investigations[0].model_provider} (Conf{" "}
                  {Math.round(exc.investigations[0].confidence * 100)}%)
                </span>
              )}
            </div>

            {!latestInv ? (
              <div className="text-sm text-slate-500">
                No investigation run yet. Click "Run Investigation Agent" to gather grounded evidence.
              </div>
            ) : (
              <div className="space-y-3 text-sm">
                <div className="p-3 rounded-lg bg-slate-50 border text-slate-800">{latestInv.summary}</div>

                <div>
                  <div className="text-xs font-semibold text-slate-700 uppercase">Verified Facts</div>
                  <ul className="list-disc pl-5 text-slate-700 mt-1 space-y-0.5">
                    {(latestInv.facts || []).map((f: string, idx: number) => (
                      <li key={idx}>{f}</li>
                    ))}
                  </ul>
                </div>

                {(latestInv.missing_information || []).length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-amber-800 uppercase">
                      Unknown / Missing Information
                    </div>
                    <ul className="list-disc pl-5 text-amber-800 mt-1 space-y-0.5">
                      {latestInv.missing_information.map((m: string, idx: number) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(latestInv.hypotheses || []).length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-slate-600 uppercase">
                      Inferred Hypotheses (Unverified)
                    </div>
                    <ul className="list-disc pl-5 text-slate-600 mt-1 space-y-0.5">
                      {latestInv.hypotheses.map((h: string, idx: number) => (
                        <li key={idx}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <div className="text-xs font-semibold text-slate-700 uppercase">
                    Evidence References
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {(latestInv.evidence_refs || []).map((ref: any, idx: number) => (
                      <span
                        key={idx}
                        className="text-xs px-2 py-1 rounded bg-slate-100 border border-slate-200 font-mono"
                      >
                        {ref.type}:{ref.label || ref.id}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900">
                  <strong>Recommended Next Action:</strong> {latestInv.recommended_action}
                </div>
              </div>
            )}
          </div>

          {/* Comments */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <h2 className="text-sm font-semibold text-slate-900">Case Discussion & Clarifications</h2>
            <ul className="space-y-2">
              {exc.comments.map((cm) => (
                <li key={cm.id} className="p-2.5 rounded-lg bg-slate-50 border text-sm">
                  <div className="text-xs text-slate-500">
                    {new Date(cm.created_at).toLocaleString()}
                    {cm.is_clarification_request ? " • Clarification Request" : ""}
                  </div>
                  <div className="mt-0.5 text-slate-800 whitespace-pre-wrap">{cm.body}</div>
                </li>
              ))}
            </ul>
            {hasPermission("exceptions:comment") && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (commentText.trim()) commentMut.mutate();
                }}
                className="space-y-2"
              >
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Add review note or clarification request..."
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  rows={2}
                />
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-xs text-slate-600">
                    <input
                      type="checkbox"
                      checked={isClarification}
                      onChange={(e) => setIsClarification(e.target.checked)}
                    />
                    Mark as clarification request
                  </label>
                  <button
                    type="submit"
                    className="px-3 py-1.5 bg-slate-800 text-white text-xs rounded-lg hover:bg-slate-900"
                  >
                    Post Note
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Right rail: Workflow Decision & Assignment */}
        <div className="lg:col-span-5 space-y-5">
          {hasPermission("exceptions:manage") && usersData?.items && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
              <h2 className="text-sm font-semibold text-slate-900">Assign Case Owner</h2>
              <select
                aria-label="Assign owner"
                value={exc.owner_id || ""}
                onChange={(e) => e.target.value && assignMut.mutate(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Unassigned</option>
                {usersData.items.map((u: any) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.roles.join(", ")})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Workflow Decision</h2>
              <p className="text-xs text-slate-500">
                Approval records a workflow decision only — never executes a bank payment.
              </p>
            </div>

            <div className="space-y-3">
              <select
                aria-label="Decision action"
                value={decisionType}
                onChange={(e) => setDecisionType(e.target.value as any)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
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
                className="w-full border border-slate-300 rounded-lg p-2.5 text-sm"
              />

              <button
                type="button"
                disabled={rationale.trim().length < 3}
                onClick={() => setConfirmOpen(true)}
                className="w-full py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                Submit Decision
              </button>
            </div>

            {confirmOpen && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 space-y-2 text-xs">
                <div className="font-semibold text-amber-900">
                  Confirm {decisionType} on case {exc.id.slice(0, 8)}?
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => decideMut.mutate()}
                    disabled={decideMut.isPending}
                    className="px-3 py-1.5 bg-indigo-600 text-white rounded font-medium"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setConfirmOpen(false)}
                    className="px-3 py-1.5 border border-slate-300 bg-white rounded"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {exc.approvals.length > 0 && (
              <div className="pt-3 border-t space-y-2">
                <div className="text-xs font-semibold text-slate-700">Decision History</div>
                {exc.approvals.map((ap) => (
                  <div key={ap.id} className="text-xs p-2 rounded bg-slate-50 border">
                    <div className="font-semibold">{ap.decision}</div>
                    <div className="text-slate-600">{ap.rationale}</div>
                    <div className="text-slate-400 mt-0.5">
                      {new Date(ap.decided_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
