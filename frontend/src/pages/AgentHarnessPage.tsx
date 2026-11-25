import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Cpu, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

const CATEGORY_STYLE: Record<string, { bg: string; border: string; color: string }> = {
  orchestrator: { bg: "#0f172a", border: "#334155", color: "#f8fafc" },
  ingestion: { bg: "#eff6ff", border: "#3b82f6", color: "#1e3a8a" },
  reconciliation: { bg: "#ecfdf5", border: "#10b981", color: "#065f46" },
  risk: { bg: "#fffbeb", border: "#f59e0b", color: "#78350f" },
  vendor: { bg: "#f5f3ff", border: "#8b5cf6", color: "#4c1d95" },
  graph: { bg: "#ecfeff", border: "#06b6d4", color: "#164e63" },
  llm: { bg: "#eef2ff", border: "#6366f1", color: "#312e81" },
  audit: { bg: "#f1f5f9", border: "#64748b", color: "#0f172a" },
  gate: { bg: "#fef2f2", border: "#ef4444", color: "#7f1d1d" },
};

export const AgentHarnessPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["agent-harness"],
    queryFn: api.getAgentHarnessOverview,
  });

  const [selectedAgentId, setSelectedAgentId] = useState<string>("DocumentAgent");
  const [selectedTraceId, setSelectedTraceId] = useState<string>("");
  const [testResult, setTestResult] = useState<any | null>(null);

  const testGeminiMut = useMutation({
    mutationFn: api.testGeminiConnection,
    onSuccess: (res) => {
      setTestResult(res);
      refetch();
    },
    onError: (e: any) =>
      setTestResult({ connected: false, error_category: "REQUEST_ERROR", message: e.message }),
  });

  const agents: any[] = data?.configured_agents || [];
  const traces: any[] = data?.recent_traces || [];
  const harnessComponents: any[] = data?.harness_components || [];
  const sys = data?.system_status;
  const gtel = data?.gemini_telemetry;

  const activeTrace = useMemo(() => {
    if (!traces.length) return null;
    return traces.find((t) => t.investigation_id === selectedTraceId) || traces[0];
  }, [traces, selectedTraceId]);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === selectedAgentId) || agents[0] || null,
    [agents, selectedAgentId]
  );

  const { rfNodes, rfEdges } = useMemo(() => {
    const chain = [
      { id: "FinanceOrchestrator", label: "Finance Orchestrator", category: "orchestrator" },
      ...agents.map((a) => ({ id: a.id, label: `${a.order}. ${a.name}`, category: a.category })),
      {
        id: "HumanApprovalGate",
        label: "Evidence-Backed Result + Human Approval Gate",
        category: "gate",
      },
    ];
    const nodes: Node[] = chain.map((item, idx) => {
      const st = CATEGORY_STYLE[item.category] || CATEGORY_STYLE.audit;
      return {
        id: item.id,
        position: { x: (idx % 3) * 260, y: Math.floor(idx / 3) * 110 },
        data: { label: item.label },
        style: {
          background: st.bg,
          border: `2px solid ${st.border}`,
          color: st.color,
          borderRadius: 10,
          fontSize: 12,
          fontWeight: 600,
          width: 225,
          padding: 10,
        },
      };
    });
    const edges: Edge[] = chain.slice(0, -1).map((item, idx) => ({
      id: `e-${item.id}-${chain[idx + 1].id}`,
      source: item.id,
      target: chain[idx + 1].id,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#64748b" },
    }));
    return { rfNodes: nodes, rfEdges: edges };
  }, [agents]);

  if (isLoading) return <div className="text-sm text-slate-500">Loading Agent Harness...</div>;
  if (error || !data) {
    return (
      <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
        Unable to load Agent Harness overview.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section 1: Hero */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-600 mb-1">
              <Cpu className="w-3.5 h-3.5" />
              <span>Intelligence • Governance &amp; Orchestration Layer</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              Inside the ReconX Intelligence Engine
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              An evidence-driven multi-agent harness that coordinates financial analysis,
              investigation and controlled decision workflows. The agent harness itself is the
              execution and governance layer—not an eighth agent.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-center">
            <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs text-slate-500">Agents</div>
              <div className="text-lg font-bold text-slate-900">{sys.configured_agents}</div>
            </div>
            <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs text-slate-500">Runs</div>
              <div className="text-lg font-bold text-slate-900">{sys.total_investigations}</div>
            </div>
            <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs text-slate-500">Succeeded</div>
              <div className="text-lg font-bold text-emerald-700">
                {sys.successful_investigations}
              </div>
            </div>
            <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs text-slate-500">Provider</div>
              <div className="text-sm font-bold text-indigo-700 uppercase">
                {sys.active_provider}
              </div>
            </div>
            <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs text-slate-500">Graph</div>
              <div className="text-sm font-bold text-slate-900">
                {sys.graph_available ? "ENABLED" : "DISABLED"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Google Gemini Integration Showcase */}
      {gtel && (
        <div className="bg-white border border-indigo-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-600">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI assistance powered by Google Gemini API</span>
              </div>
              <h2 className="text-lg font-bold text-slate-900 mt-0.5">
                Google Gemini Integration
              </h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Document Evidence → Deterministic Finance Engine → Gemini-assisted Investigation →
                Evidence Validation → Human Approval
              </p>
            </div>
            {hasPermission("admin:config:write") && (
              <button
                type="button"
                onClick={() => testGeminiMut.mutate()}
                disabled={testGeminiMut.isPending}
                className="px-3.5 py-2 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50"
              >
                {testGeminiMut.isPending ? "Testing Gemini..." : "Test Gemini Connection"}
              </button>
            )}
          </div>

          {testResult && (
            <div
              className={`p-3 rounded-lg border text-xs ${
                testResult.connected
                  ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                  : "bg-amber-50 border-amber-200 text-amber-900"
              }`}
            >
              <strong>{testResult.connected ? "Connected" : "Connection Failed"}:</strong>{" "}
              {testResult.message} (Model: {testResult.model || gtel.gemini_model}, Latency:{" "}
              {testResult.latency_ms ?? 0} ms, Category: {testResult.error_category})
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Gemini Model</div>
              <div className="font-bold text-slate-900 truncate">{gtel.gemini_model}</div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Configured / Key</div>
              <div className="font-bold text-slate-900 uppercase">
                {gtel.configured_provider} ({gtel.api_key_configured ? "Key Set" : "No Key"})
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Invocations</div>
              <div className="font-bold text-slate-900">{gtel.invocation_count}</div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Succeeded</div>
              <div className="font-bold text-emerald-700">{gtel.successful_calls}</div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Failed / Fallback</div>
              <div className="font-bold text-amber-700">
                {gtel.failed_calls} / {gtel.fallback_count}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Avg Latency</div>
              <div className="font-bold text-slate-900">{gtel.avg_latency_ms} ms</div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-slate-500">Token Usage</div>
              <div className="font-semibold text-slate-600">Unavailable</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded-lg bg-indigo-50/50 border border-indigo-100">
              <div className="font-bold text-indigo-900 mb-1">Where Gemini Assists</div>
              <ul className="list-disc pl-4 text-slate-700 space-y-0.5">
                <li>Natural-language investigation summaries over DB-verified facts</li>
                <li>Contextual interpretation of discrepancies and vendor history</li>
                <li>Clearly labeled unverified hypotheses and recommended next steps</li>
              </ul>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <div className="font-bold text-slate-900 mb-1">What Gemini Never Does</div>
              <ul className="list-disc pl-4 text-slate-700 space-y-0.5">
                <li>Never calculates authoritative totals or overrides 3-way matching</li>
                <li>Never creates unvalidated evidence refs, approves invoices, or pays</li>
                <li>Never bypasses RBAC, maker-checker, or audit immutability</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Section 2: Interactive Agent Architecture + Right Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-1">
            Seven-Stage Investigation Pipeline (Click an Agent Node to Inspect)
          </h2>
          <p className="text-xs text-slate-500 mb-3">
            Verified order in <code>FinanceOrchestrator.run_pipeline()</code>
          </p>
          <div className="hidden sm:block h-80 border border-slate-200 rounded-lg">
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              fitView
              onNodeClick={(_, node) => {
                if (agents.some((a) => a.id === node.id)) {
                  setSelectedAgentId(node.id);
                }
              }}
            >
              <Background />
              <Controls />
            </ReactFlow>
          </div>
          <ol className="sm:hidden space-y-2 text-xs">
            {agents.map((a) => (
              <li
                key={a.id}
                onClick={() => setSelectedAgentId(a.id)}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
              >
                {a.order}. {a.name}
              </li>
            ))}
          </ol>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-2">Agent Inspector</h2>
          {selectedAgent ? (
            <div className="space-y-2.5 text-xs">
              <div className="text-base font-bold text-indigo-700">{selectedAgent.name}</div>
              <p className="text-slate-700">{selectedAgent.purpose}</p>
              <div>
                <span className="font-semibold text-slate-800">Input Context:</span>{" "}
                <span className="text-slate-600">{selectedAgent.input_context}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-800">Processing:</span>{" "}
                <span className="text-slate-600">{selectedAgent.processing}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-800">Tools:</span>{" "}
                <span className="font-mono text-slate-700">{selectedAgent.tools.join(", ")}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-800">Output:</span>{" "}
                <span className="text-slate-600">{selectedAgent.output}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-800">Mode:</span>{" "}
                <span className="text-slate-600">{selectedAgent.execution_mode}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-800">Failure &amp; Recovery:</span>{" "}
                <span className="text-slate-600">{selectedAgent.failure_recovery}</span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500">Select an agent node to inspect.</div>
          )}
        </div>
      </div>

      {/* Section 3: Agent Detail Cards */}
      <div>
        <h2 className="text-sm font-semibold text-slate-900 mb-3">
          Configured Pipeline Agents ({agents.length})
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {agents.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setSelectedAgentId(a.id)}
              className={`text-left p-4 rounded-xl border transition shadow-sm bg-white ${
                selectedAgentId === a.id
                  ? "border-indigo-500 ring-1 ring-indigo-500"
                  : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <div className="text-xs font-semibold text-indigo-600">Stage {a.order}</div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">{a.name}</div>
              <p className="text-xs text-slate-600 mt-1">{a.purpose}</p>
              <div className="mt-2 text-[11px] font-mono text-slate-500 truncate">
                {a.tools.join(" • ")}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Section 4: Harness Infrastructure */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">
          Harness Infrastructure (Governance Surrounding the 7 Agents)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {harnessComponents.map((hc) => (
            <div key={hc.name} className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs font-bold text-slate-900">{hc.name}</div>
              <div className="text-xs text-slate-600 mt-1">{hc.role}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 5: Live Execution Trace Explorer */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Live Execution Trace Explorer</h2>
            <p className="text-xs text-slate-500">
              Persisted investigation runs with stage-by-stage traces and provider provenance.
            </p>
          </div>
          {traces.length > 0 && (
            <select
              aria-label="Select investigation trace"
              value={activeTrace?.investigation_id || ""}
              onChange={(e) => setSelectedTraceId(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
            >
              {traces.map((t) => (
                <option key={t.investigation_id} value={t.investigation_id}>
                  {t.case_type} ({t.model_provider}/{t.model_name}) — {t.created_at.slice(0, 19)}
                </option>
              ))}
            </select>
          )}
        </div>

        {!activeTrace ? (
          <div className="p-6 text-center rounded-lg border border-dashed border-slate-300 text-xs text-slate-500">
            No persisted investigation runs yet. Open an Exception case and click{" "}
            <strong>Run Investigation</strong> to record a live execution trace.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <StatusBadge value={activeTrace.status} />
              <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-800 font-semibold uppercase">
                Actual Provider: {activeTrace.actual_provider || activeTrace.model_provider} (
                {activeTrace.model_name})
              </span>
              {activeTrace.actual_provider === "gemini" && !activeTrace.fallback_used ? (
                <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                  Generated with Google Gemini
                </span>
              ) : activeTrace.fallback_used ? (
                <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold">
                  Mock fallback used — not Gemini-generated.
                </span>
              ) : null}
              <span className="text-slate-600">
                Confidence: {(activeTrace.confidence * 100).toFixed(0)}%
              </span>
              <span className="text-slate-600">
                Human Approval Required: {String(activeTrace.human_approval_required)}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800">
              {activeTrace.summary}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Stage Agent</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Duration</th>
                    <th className="py-2 px-3">Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(activeTrace.execution_trace || []).map((st: any, i: number) => (
                    <tr key={`${st.agent}-${i}`}>
                      <td className="py-2 px-3 font-semibold text-slate-900">{st.agent}</td>
                      <td className="py-2 px-3">
                        <StatusBadge value={st.status} />
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-600">{st.duration_ms} ms</td>
                      <td className="py-2 px-3 text-slate-700">{st.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Section 6: Safety & Trust Boundaries */}
      <div className="bg-slate-900 text-slate-100 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 text-amber-400 text-sm font-bold mb-2">
          <ShieldAlert className="w-4 h-4" />
          <span>AI RECOMMENDATION ≠ FINANCIAL AUTHORIZATION</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-slate-300">
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>All financial totals, taxes, and tolerances run in pure decimal.Decimal.</span>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>Document text is fenced as untrusted evidence; zero SQL or pay tools.</span>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>Evidence references are post-validated against org-scoped DB rows.</span>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>RBAC, maker-checker, and append-only audit triggers enforce governance.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
