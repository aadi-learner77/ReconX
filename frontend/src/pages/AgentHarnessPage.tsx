import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Cpu, Lock, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Badge,
  Button,
  Card,
  Drawer,
  EmptyState,
  PageCaption,
  PageSkeleton,
  Stat,
  StatusPill,
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
  const [selectedFlowNode, setSelectedFlowNode] = useState<any | null>(null);
  const [telemetryStage, setTelemetryStage] = useState<any | null>(null);
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
  const graphSync = sys?.graph_sync;

  const activeTrace = useMemo(() => {
    if (!traces.length) return null;
    return traces.find((t) => t.investigation_id === selectedTraceId) || traces[0];
  }, [traces, selectedTraceId]);

  const { data: neo4jRunGraph } = useQuery({
    queryKey: ["agent-neo4j-graph", activeTrace?.investigation_id],
    queryFn: () => api.getAgentGraphExecution(activeTrace!.investigation_id),
    enabled: Boolean(activeTrace?.investigation_id),
  });

  const { data: crossAnalytics } = useQuery({
    queryKey: ["agent-cross-analytics"],
    queryFn: api.getAgentGraphAnalytics,
  });

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

  const { rfNodes, rfEdges, graphIsNeo4j } = useMemo(() => {
    if (neo4jRunGraph?.nodes?.length > 0) {
      const nodes: Node[] = neo4jRunGraph.nodes.map((n: any, idx: number) => ({
        id: n.id,
        position: { x: (idx % 4) * 255, y: Math.floor(idx / 4) * 120 },
        data: { label: `${n.type}: ${n.label}`, raw: n },
        style: flowNodeStyle(n.type, selectedFlowNode?.id === n.id),
      }));
      const edges: Edge[] = (neo4jRunGraph.edges || []).map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        labelStyle: { fontSize: 10, fill: "var(--ink-500)", fontFamily: "JetBrains Mono, monospace" },
        markerEnd: { type: MarkerType.ArrowClosed },
        style: flowEdgeStyle(false),
      }));
      return { rfNodes: nodes, rfEdges: edges, graphIsNeo4j: neo4jRunGraph.source === "neo4j" };
    }

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
    return { rfNodes: nodes, rfEdges: edges, graphIsNeo4j: false };
  }, [neo4jRunGraph, agents, selectedAgentId, selectedFlowNode]);

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
          module="Intelligence / Neo4j Agent Execution Graph"
          index={
            graphSync?.neo4j_connected
              ? `Neo4j Connected (${graphSync.nodes_synchronized} nodes)`
              : "7-Stage Evidence Harness"
          }
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
              Coordinates financial analysis, investigation, and controlled decision workflows.
              Persisted runs, stage executions, tool calls, and evidence citations are synchronized
              to Neo4j.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Stat label="Agents" value={sys.configured_agents} className="p-3.5" />
            <Stat label="Runs" value={sys.total_investigations} className="p-3.5" />
            <Stat label="Succeeded" value={sys.successful_investigations} tone="success" className="p-3.5" />
            <Stat label="Provider" value={String(sys.active_provider).toUpperCase()} mono className="p-3.5" />
            <Stat
              label="Neo4j"
              value={graphSync?.neo4j_connected ? "ONLINE" : "OFFLINE"}
              tone={graphSync?.neo4j_connected ? "success" : "warning"}
              mono
              className="p-3.5"
            />
          </div>
        </div>
      </Card>

      {/* Horizontal Animated 7-Stage Pipeline + Brass Human Gate */}
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
            Seven-Stage Execution Pipeline + Human Approval Gate (Click stage for telemetry)
          </div>
          <div className="flex items-center gap-2 text-[11px] font-mono text-ink-500">
            <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-status-success-fg" /> done</span>
            <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-status-info-fg" /> running</span>
            <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-status-warning-fg" /> fallback</span>
            <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sand-400" /> idle</span>
          </div>
        </div>
        <div className="overflow-x-auto pb-2">
          <div className="inline-flex items-center gap-2 min-w-max">
            {stepperItems.map((step, idx) => {
              const isGate = step.id === "HumanApprovalGate";
              const traceStep = ((activeTrace?.execution_trace as any[]) || []).find(
                (t) => t.agent === step.id || t.agent === step.label.replace(/^\d+\.\s*/, "")
              );
              const isSelected = selectedAgentId === step.id;
              const ringClass =
                step.state === "done"
                  ? "ring-2 ring-status-success-fg/70"
                  : step.state === "running"
                    ? "ring-2 ring-status-info-fg animate-pulse"
                    : step.state === "fallback"
                      ? "ring-2 ring-status-warning-fg/80"
                      : "ring-1 ring-sand-300";

              return (
                <React.Fragment key={step.id}>
                  <motion.button
                    type="button"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.04, duration: 0.2 }}
                    onClick={() => {
                      if (!isGate && agents.some((a) => a.id === step.id)) {
                        setSelectedAgentId(step.id);
                      }
                      setTelemetryStage({
                        id: step.id,
                        label: step.label,
                        state: step.state,
                        isGate,
                        duration_ms: traceStep?.duration_ms ?? null,
                        provider:
                          activeTrace?.model_provider || sys?.active_provider || "mock",
                        fallback_used: step.state === "fallback",
                        tokens: traceStep?.tokens ?? "Unavailable",
                        summary:
                          traceStep?.summary ||
                          (isGate
                            ? "Deterministic maker-checker human approval gate. AI cannot approve or pay."
                            : "Stage ready in orchestrator."),
                      });
                    }}
                    className={`rounded-card px-3.5 py-2.5 text-left transition-all min-w-[148px] ${
                      isGate
                        ? "border-2 border-status-warning-fg bg-status-warning-bg/35 text-ink-900 shadow-card"
                        : isSelected
                          ? `bg-ink-900 text-on-ink ${ringClass}`
                          : `bg-paper text-ink-900 border border-sand-200 hover:border-sand-400 ${ringClass}`
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold truncate">{step.label}</span>
                      {isGate && <Lock className="w-3.5 h-3.5 text-status-warning-fg shrink-0" />}
                    </div>
                    <div
                      className={`mt-1 font-mono text-[10px] ${
                        isSelected && !isGate ? "text-on-ink/75" : "text-ink-500"
                      }`}
                    >
                      {traceStep?.duration_ms !== undefined
                        ? `${traceStep.duration_ms} ms`
                        : step.state.toUpperCase()}
                    </div>
                  </motion.button>
                  {idx < stepperItems.length - 1 && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: idx * 0.04 }}
                      className="text-ink-500 font-mono text-xs select-none px-0.5"
                      aria-hidden="true"
                    >
                      ──▶
                    </motion.span>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Expandable Stage Telemetry Drawer */}
      <Drawer
        open={Boolean(telemetryStage)}
        onClose={() => setTelemetryStage(null)}
        title={telemetryStage?.label || "Stage Telemetry"}
        subtitle={telemetryStage?.isGate ? "Human Governance Gate" : "Agent Stage Execution Telemetry"}
      >
        {telemetryStage && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between">
              <StatusPill value={telemetryStage.state.toUpperCase()} />
              {telemetryStage.isGate && (
                <Badge value="Human Gate · Brass Guard" tone="warning" />
              )}
            </div>
            <div className="rounded-card border border-sand-200 bg-sand-50 p-4 space-y-2.5 font-mono">
              <div className="flex justify-between">
                <span className="text-ink-500">Provider</span>
                <span className="font-semibold text-ink-900 uppercase">{telemetryStage.provider}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-500">Duration</span>
                <span className="font-semibold text-ink-900">
                  {telemetryStage.duration_ms !== null ? `${telemetryStage.duration_ms} ms` : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-500">Tokens</span>
                <span className="font-semibold text-ink-900">{String(telemetryStage.tokens)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-500">Fallback Used</span>
                <span className="font-semibold text-ink-900">
                  {telemetryStage.fallback_used ? "YES" : "NO"}
                </span>
              </div>
            </div>
            <div className="p-3.5 rounded-card border border-sand-200 bg-paper text-ink-700 leading-relaxed">
              {telemetryStage.summary}
            </div>
          </div>
        )}
      </Drawer>

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
        </Card>
      )}

      {/* Interactive Neo4j Execution Graph + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-lg font-bold text-ink-900">
                {graphIsNeo4j
                  ? "Neo4j Investigation Execution Graph (Real Persisted Run)"
                  : "Seven-Stage Investigation Pipeline (Click an Agent Node to Inspect)"}
              </h2>
              <p className="text-xs text-ink-500">
                {graphIsNeo4j
                  ? "Live Neo4j graph: AgentRun → AgentStageExecution → ToolCall & EvidenceReference"
                  : "Run an investigation on an exception to inspect its live Neo4j execution graph."}
              </p>
            </div>
            {graphIsNeo4j && <StatusPill value="NEO4J LIVE" tone="success" />}
          </div>
          <div className="hidden sm:block h-96 border border-sand-200 rounded-card bg-sand-50 overflow-hidden">
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              onNodeClick={(_, node) => {
                const raw = (node.data as any)?.raw;
                if (raw) {
                  setSelectedFlowNode(raw);
                  const matched = agents.find((a) => a.id === raw.data?.agent_name);
                  if (matched) setSelectedAgentId(matched.id);
                } else if (agents.some((a) => a.id === node.id)) {
                  setSelectedFlowNode(null);
                  setSelectedAgentId(node.id);
                }
              }}
            >
              <Background color="var(--sand-200)" gap={18} />
              <Controls style={flowControlStyle} />
            </ReactFlow>
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="font-display text-lg font-bold text-ink-900">
            {selectedFlowNode ? `${selectedFlowNode.type} Inspector` : "Agent Inspector"}
          </h2>
          {selectedFlowNode ? (
            <div className="space-y-2.5 text-xs">
              <div className="font-display text-base font-bold text-ink-900">
                {selectedFlowNode.label}
              </div>
              <div className="p-3 rounded-control bg-sand-50 border border-sand-200 space-y-1.5">
                {Object.entries(selectedFlowNode.data || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-ink-500">{k}</span>
                    <span className="font-mono text-ink-900 text-right break-all">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
              <Button variant="outline" size="sm" onClick={() => setSelectedFlowNode(null)}>
                Back to Agent Definition
              </Button>
            </div>
          ) : selectedAgent ? (
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
              {selectedAgent.id === "RiskAgent" && (
                <div className="p-2.5 rounded-control bg-status-info-bg text-status-info-fg font-semibold">
                  Risk indicators, not proof of fraud.
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-ink-500">Select an agent or execution node to inspect.</div>
          )}
        </Card>
      </div>

      {/* Cross-Investigation Explorer (Neo4j Cypher) */}
      {crossAnalytics && (
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-lg font-bold text-ink-900">
                Cross-Investigation Relationship Explorer (Neo4j)
              </h2>
              <p className="text-xs text-ink-500">
                Repeated vendor investigations, shared evidence citations, and stage execution health.
              </p>
            </div>
            <StatusPill
              value={crossAnalytics.source === "neo4j" ? "NEO4J CYPHER" : "UNAVAILABLE"}
              tone={crossAnalytics.source === "neo4j" ? "success" : "warning"}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3.5 rounded-card bg-sand-50 border border-sand-200 space-y-2">
              <div className="font-semibold uppercase tracking-[0.08em] text-[11px] text-ink-500">
                Investigations by Vendor
              </div>
              {(crossAnalytics.vendor_investigations || []).length === 0 ? (
                <div className="text-ink-500">No vendor investigations synced yet.</div>
              ) : (
                crossAnalytics.vendor_investigations.map((v: any, i: number) => (
                  <div key={i} className="flex justify-between gap-2 border-b border-sand-200 pb-1 last:border-b-0">
                    <span className="font-medium text-ink-900 truncate">{v.vendor_name}</span>
                    <span className="font-mono font-bold text-ink-900">{v.investigation_count}</span>
                  </div>
                ))
              )}
            </div>
            <div className="p-3.5 rounded-card bg-sand-50 border border-sand-200 space-y-2">
              <div className="font-semibold uppercase tracking-[0.08em] text-[11px] text-ink-500">
                Shared Evidence Citations
              </div>
              {(crossAnalytics.shared_evidence || []).length === 0 ? (
                <div className="text-ink-500">No evidence references synced yet.</div>
              ) : (
                crossAnalytics.shared_evidence.map((e: any, i: number) => (
                  <div key={i} className="flex justify-between gap-2 border-b border-sand-200 pb-1 last:border-b-0 font-mono">
                    <span className="truncate text-ink-900">{e.label}</span>
                    <span className="font-bold text-ink-900">{e.cite_count}</span>
                  </div>
                ))
              )}
            </div>
            <div className="p-3.5 rounded-card bg-sand-50 border border-sand-200 space-y-2">
              <div className="font-semibold uppercase tracking-[0.08em] text-[11px] text-ink-500">
                Stage Execution Reliability
              </div>
              {(crossAnalytics.stage_stats || []).length === 0 ? (
                <div className="text-ink-500">No stage executions synced yet.</div>
              ) : (
                crossAnalytics.stage_stats.map((s: any, i: number) => (
                  <div key={i} className="flex justify-between gap-2 border-b border-sand-200 pb-1 last:border-b-0 font-mono">
                    <span className="text-ink-900">{s.agent_name}</span>
                    <span className="text-status-success-fg">
                      {s.succeeded}/{s.total_runs}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </Card>
      )}

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
              onChange={(e) => {
                setSelectedFlowNode(null);
                setSelectedTraceId(e.target.value);
              }}
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
