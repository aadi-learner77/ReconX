import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Cpu, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Button,
  Card,
  EmptyState,
  PageCaption,
  PageSkeleton,
  Stat,
  StatusPill,
  Stepper,
  type StepItem,
} from "../components/ui";
import { flowControlStyle, flowEdgeStyle, flowNodeStyle } from "../theme/flowTheme";

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

  const stepperItems: StepItem[] = useMemo(() => {
    const traceMap = new Map<string, string>(
      ((activeTrace?.execution_trace as any[]) || []).map((st) => [st.agent, st.status])
    );
    const items: StepItem[] = agents.map((a) => {
      const st = (traceMap.get(a.id) || traceMap.get(a.name) || "").toUpperCase();
      const state: StepItem["state"] =
        st === "FALLBACK"
          ? "fallback"
          : st === "RUNNING"
            ? "running"
            : st === "DONE" || st === "SUCCEEDED" || st === "COMPLETED"
              ? "done"
              : "idle";
      return { id: a.id, label: `${a.order}. ${a.name}`, state };
    });
    items.push({ id: "HumanApprovalGate", label: "Human Approval Gate", state: "idle" });
    return items;
  }, [agents, activeTrace]);

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
    const nodes: Node[] = chain.map((item, idx) => ({
      id: item.id,
      position: { x: (idx % 3) * 260, y: Math.floor(idx / 3) * 115 },
      data: { label: item.label },
      style: flowNodeStyle(item.category, selectedAgentId === item.id),
    }));
    const edges: Edge[] = chain.slice(0, -1).map((item, idx) => ({
      id: `e-${item.id}-${chain[idx + 1].id}`,
      source: item.id,
      target: chain[idx + 1].id,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: flowEdgeStyle(false),
    }));
    return { rfNodes: nodes, rfEdges: edges };
  }, [agents, selectedAgentId]);

  if (isLoading) return <PageSkeleton />;
  if (error || !data) {
    return (
      <Card className="border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-sm">
        Unable to load Agent Harness overview.
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <Card variant="hero">
        <PageCaption
          module="Intelligence / Governance & Orchestration"
          index="7-Stage Evidence Harness"
        />
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 mb-1">
              <Cpu className="w-3.5 h-3.5 text-ink-900" />
              <span>Evidence-Driven Orchestration Layer</span>
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-bold text-ink-900">
              Inside the ReconX Intelligence Engine
            </h1>
            <p className="text-sm text-ink-700 mt-2">
              Coordinates financial analysis, investigation, and controlled decision workflows. The
              agent harness itself is the execution and governance layer — not an eighth agent.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Stat label="Agents" value={sys.configured_agents} className="p-3.5" />
            <Stat label="Runs" value={sys.total_investigations} className="p-3.5" />
            <Stat label="Succeeded" value={sys.successful_investigations} tone="success" className="p-3.5" />
            <Stat label="Provider" value={String(sys.active_provider).toUpperCase()} mono className="p-3.5" />
            <Stat label="Graph" value={sys.graph_available ? "ON" : "OFF"} mono className="p-3.5" />
          </div>
        </div>
      </Card>

      {/* Horizontal 7-Stage Stepper */}
      <Card className="space-y-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
          Seven-Stage Execution Pipeline + Human Gate
        </div>
        <Stepper
          steps={stepperItems}
          activeId={selectedAgentId}
          onSelect={(id) => {
            if (agents.some((a) => a.id === id)) setSelectedAgentId(id);
          }}
        />
      </Card>

      {/* Google Gemini Integration Showcase */}
      {gtel && (
        <Card className="space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                <Sparkles className="w-3.5 h-3.5 text-ink-900" />
                <span>AI Assistance Powered by Google Gemini API</span>
              </div>
              <h2 className="font-display text-2xl font-bold text-ink-900 mt-0.5">
                Google Gemini Integration
              </h2>
              <p className="text-xs text-ink-700 mt-1 font-mono">
                Document Evidence → Deterministic Finance Engine → Gemini Investigation → Evidence
                Validation → Human Approval
              </p>
            </div>
            {hasPermission("admin:config:write") && (
              <Button onClick={() => testGeminiMut.mutate()} disabled={testGeminiMut.isPending}>
                {testGeminiMut.isPending ? "Testing Gemini..." : "Test Gemini Connection"}
              </Button>
            )}
          </div>

          {testResult && (
            <div
              className={`p-3.5 rounded-control border text-xs font-mono ${
                testResult.connected
                  ? "bg-status-success-bg border-status-success-fg/30 text-status-success-fg"
                  : "bg-status-warning-bg border-status-warning-fg/30 text-status-warning-fg"
              }`}
            >
              <strong>{testResult.connected ? "Connected" : "Connection Failed"}:</strong>{" "}
              {testResult.message} (Model: {testResult.model || gtel.gemini_model}, Latency:{" "}
              {testResult.latency_ms ?? 0} ms, Category: {testResult.error_category})
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 text-xs">
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Gemini Model</div>
              <div className="font-mono font-bold text-ink-900 truncate mt-1">{gtel.gemini_model}</div>
            </div>
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Configured / Key</div>
              <div className="font-mono font-bold text-ink-900 uppercase mt-1">
                {gtel.configured_provider} ({gtel.api_key_configured ? "Key Set" : "No Key"})
              </div>
            </div>
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Invocations</div>
              <div className="font-mono font-bold text-ink-900 mt-1">{gtel.invocation_count}</div>
            </div>
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Succeeded</div>
              <div className="font-mono font-bold text-status-success-fg mt-1">
                {gtel.successful_calls}
              </div>
            </div>
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Failed / Fallback</div>
              <div className="font-mono font-bold text-status-warning-fg mt-1">
                {gtel.failed_calls} / {gtel.fallback_count}
              </div>
            </div>
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Avg Latency</div>
              <div className="font-mono font-bold text-ink-900 mt-1">{gtel.avg_latency_ms} ms</div>
            </div>
            <div className="p-3 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-ink-500">Token Usage</div>
              <div className="font-mono font-semibold text-ink-500 mt-1">Unavailable</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-card bg-sand-50 border border-sand-200">
              <div className="font-semibold text-ink-900 mb-1.5">Where Gemini Assists</div>
              <ul className="list-disc pl-4 text-ink-700 space-y-1">
                <li>Natural-language investigation summaries over DB-verified facts</li>
                <li>Contextual interpretation of discrepancies and vendor history</li>
                <li>Clearly labeled unverified hypotheses and recommended next steps</li>
              </ul>
            </div>
            <div className="p-4 rounded-card bg-sand-100 border border-sand-200">
              <div className="font-semibold text-ink-900 mb-1.5">What Gemini Never Does</div>
              <ul className="list-disc pl-4 text-ink-700 space-y-1">
                <li>Never calculates authoritative totals or overrides 3-way matching</li>
                <li>Never creates unvalidated evidence refs, approves invoices, or pays</li>
                <li>Never bypasses RBAC, maker-checker, or audit immutability</li>
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* Interactive Agent Architecture + Right Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <h2 className="font-display text-lg font-bold text-ink-900 mb-1">
            Seven-Stage Investigation Pipeline (Click an Agent Node to Inspect)
          </h2>
          <p className="text-xs text-ink-500 mb-3">
            Verified order in <code className="font-mono">FinanceOrchestrator.run_pipeline()</code>
          </p>
          <div className="hidden sm:block h-80 border border-sand-200 rounded-card bg-sand-50 overflow-hidden">
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
              <Background color="var(--sand-200)" gap={18} />
              <Controls style={flowControlStyle} />
            </ReactFlow>
          </div>
          <ol className="sm:hidden space-y-2 text-xs">
            {agents.map((a) => (
              <li
                key={a.id}
                onClick={() => setSelectedAgentId(a.id)}
                className="p-2.5 rounded-control border border-sand-200 bg-sand-50 font-medium"
              >
                {a.order}. {a.name}
              </li>
            ))}
          </ol>
        </Card>

        <Card>
          <h2 className="font-display text-lg font-bold text-ink-900 mb-3">Agent Inspector</h2>
          {selectedAgent ? (
            <div className="space-y-3 text-xs">
              <div className="font-display text-lg font-bold text-ink-900">{selectedAgent.name}</div>
              <p className="text-ink-700">{selectedAgent.purpose}</p>
              <div>
                <span className="font-semibold text-ink-900">Input Context:</span>{" "}
                <span className="text-ink-700">{selectedAgent.input_context}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-900">Processing:</span>{" "}
                <span className="text-ink-700">{selectedAgent.processing}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-900">Tools:</span>{" "}
                <span className="font-mono text-ink-700">{selectedAgent.tools.join(", ")}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-900">Output:</span>{" "}
                <span className="text-ink-700">{selectedAgent.output}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-900">Mode:</span>{" "}
                <span className="font-mono text-ink-700">{selectedAgent.execution_mode}</span>
              </div>
              <div>
                <span className="font-semibold text-ink-900">Failure &amp; Recovery:</span>{" "}
                <span className="text-ink-700">{selectedAgent.failure_recovery}</span>
              </div>
              {selectedAgent.id === "RiskAgent" && (
                <div className="p-2.5 rounded-control bg-status-info-bg text-status-info-fg font-semibold">
                  Risk indicators, not proof of fraud.
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-ink-500">Select an agent node to inspect.</div>
          )}
        </Card>
      </div>

      {/* Harness Infrastructure */}
      <Card>
        <h2 className="font-display text-lg font-bold text-ink-900 mb-3">
          Harness Infrastructure (Governance Surrounding the 7 Agents)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {harnessComponents.map((hc) => (
            <div key={hc.name} className="p-3.5 rounded-control bg-sand-50 border border-sand-200">
              <div className="text-xs font-bold text-ink-900">{hc.name}</div>
              <div className="text-xs text-ink-700 mt-1">{hc.role}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Live Execution Trace Explorer */}
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-bold text-ink-900">
              Live Execution Trace Explorer
            </h2>
            <p className="text-xs text-ink-500">
              Persisted investigation runs with stage-by-stage traces and provider provenance. Risk
              indicators, not proof of fraud.
            </p>
          </div>
          {traces.length > 0 && (
            <select
              aria-label="Select investigation trace"
              value={activeTrace?.investigation_id || ""}
              onChange={(e) => setSelectedTraceId(e.target.value)}
              className="px-3 py-2 rounded-control border border-sand-200 text-xs bg-sand-50 font-mono"
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
          <EmptyState
            title="No persisted investigation runs yet"
            description="Open an Exception case and click Run Investigation Agent to record a live execution trace."
          />
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <StatusPill value={activeTrace.status} />
              <span className="px-2.5 py-1 rounded-full bg-sand-100 border border-sand-200 font-mono font-semibold text-ink-900 uppercase">
                Actual Provider: {activeTrace.actual_provider || activeTrace.model_provider} (
                {activeTrace.model_name})
              </span>
              {activeTrace.actual_provider === "gemini" && !activeTrace.fallback_used ? (
                <StatusPill value="Generated with Google Gemini" tone="success" />
              ) : activeTrace.fallback_used ? (
                <StatusPill value="Mock fallback used — not Gemini-generated" tone="warning" />
              ) : null}
              <span className="font-mono text-ink-700">
                Confidence: {(activeTrace.confidence * 100).toFixed(0)}%
              </span>
              <span className="font-mono text-ink-700">
                Human Approval Required: {String(activeTrace.human_approval_required)}
              </span>
            </div>

            <div className="p-3.5 rounded-control bg-sand-50 border border-sand-200 text-xs text-ink-900">
              {activeTrace.summary}
            </div>

            <div className="overflow-x-auto rounded-card border border-sand-200">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-sand-100 text-ink-500 border-b border-sand-200">
                  <tr>
                    <th scope="col" className="py-2.5 px-3">Stage Agent</th>
                    <th scope="col" className="py-2.5 px-3">Status</th>
                    <th scope="col" className="py-2.5 px-3">Duration</th>
                    <th scope="col" className="py-2.5 px-3">Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sand-200">
                  {(activeTrace.execution_trace || []).map((st: any, i: number) => (
                    <tr key={`${st.agent}-${i}`}>
                      <td className="py-2.5 px-3 font-semibold text-ink-900">{st.agent}</td>
                      <td className="py-2.5 px-3">
                        <StatusPill value={st.status} />
                      </td>
                      <td className="py-2.5 px-3 text-ink-700">{st.duration_ms} ms</td>
                      <td className="py-2.5 px-3 text-ink-700 font-sans">{st.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      {/* Safety & Trust Boundaries Footer */}
      <div className="bg-ink-900 text-on-ink rounded-hero p-6 shadow-soft space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.08em]">
          <ShieldAlert className="w-4 h-4" />
          <span>AI RECOMMENDATION ≠ FINANCIAL AUTHORIZATION • AI never approves, matches, or pays</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs opacity-90">
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
            <span>All financial totals, taxes, and tolerances run in pure decimal.Decimal.</span>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
            <span>Document text is fenced as untrusted evidence; zero SQL or pay tools.</span>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
            <span>Evidence references are post-validated against org-scoped DB rows.</span>
          </div>
          <div className="flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
            <span>RBAC, maker-checker, and append-only audit triggers enforce governance.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
