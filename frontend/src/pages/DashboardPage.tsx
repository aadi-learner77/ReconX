import React, { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { animate, motion } from "framer-motion";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  ArrowUpRight,
  Clock,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { api } from "../api/client";
import {
  Badge,
  Card,
  EmptyState,
  PageCaption,
  Skeleton,
  StatusPill,
} from "../components/ui";
import { chartTheme } from "../theme/chartTheme";
import { formatInrString } from "../utils/money";

function sumDecimalStrings(values: Array<string | null | undefined>): string {
  let totalPaise = 0n;
  for (const raw of values) {
    if (!raw) continue;
    const cleaned = String(raw).trim();
    const m = cleaned.match(/^(-?)(\d+)(?:\.(\d+))?$/);
    if (!m) continue;
    const sign = m[1] === "-" ? -1n : 1n;
    const whole = BigInt(m[2]);
    const frac = BigInt((m[3] || "").padEnd(2, "0").slice(0, 2));
    totalPaise += sign * (whole * 100n + frac);
  }
  const neg = totalPaise < 0n ? "-" : "";
  const abs = totalPaise < 0n ? -totalPaise : totalPaise;
  const wholeOut = abs / 100n;
  const fracOut = (abs % 100n).toString().padStart(2, "0");
  return `${neg}${wholeOut.toString()}.${fracOut}`;
}

const AnimatedCount: React.FC<{ value: number; suffix?: string }> = ({ value, suffix = "" }) => {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const controls = animate(0, value, {
      duration: 0.7,
      ease: [0.2, 0.8, 0.2, 1],
      onUpdate: (latest) => setDisplay(Math.round(latest)),
    });
    return () => controls.stop();
  }, [value]);

  return (
    <span className="font-mono tabular-nums">
      {display}
      {suffix}
    </span>
  );
};

const MiniSparkline: React.FC<{ points: number[]; color?: string }> = ({
  points,
  color = "var(--ink-900)",
}) => {
  const safe = points.length >= 2 ? points : [0, ...points, 0];
  const max = Math.max(...safe, 1);
  const min = Math.min(...safe, 0);
  const span = Math.max(max - min, 1);
  const coords = safe
    .map((v, i) => {
      const x = (i / (safe.length - 1)) * 72;
      const y = 22 - ((v - min) / span) * 18;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 72 24" className="w-18 h-6 shrink-0" aria-hidden="true">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={coords}
      />
    </svg>
  );
};

const BentoChartTooltip: React.FC<{
  active?: boolean;
  payload?: Array<{ value: number; payload?: { stage?: string; rule?: string } }>;
  label?: string;
}> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
  return (
    <div className="rounded-card border border-sand-200 bg-paper px-3 py-2 shadow-floating text-xs">
      <div className="font-semibold text-ink-900">{label || item.payload?.stage || item.payload?.rule}</div>
      <div className="font-mono tabular-nums text-ink-700 mt-0.5">Count: {item.value}</div>
    </div>
  );
};

function formatSlaCountdown(createdAtIso: string): { label: string; urgent: boolean } {
  const createdMs = new Date(createdAtIso).getTime();
  if (Number.isNaN(createdMs)) return { label: "48h SLA", urgent: false };
  const deadlineMs = createdMs + 48 * 3600 * 1000;
  const remainingMs = deadlineMs - Date.now();
  if (remainingMs <= 0) {
    const overdueHrs = Math.abs(Math.floor(remainingMs / 3600000));
    return { label: `Overdue ${overdueHrs}h`, urgent: true };
  }
  const hrs = Math.floor(remainingMs / 3600000);
  const mins = Math.floor((remainingMs % 3600000) / 60000);
  return { label: `${hrs}h ${mins}m left`, urgent: hrs < 8 };
}

export const DashboardPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.dashboardSummary,
  });

  const { data: exceptionsPage } = useQuery({
    queryKey: ["dashboard-exceptions"],
    queryFn: () => api.listExceptions(),
  });

  const { data: harnessData } = useQuery({
    queryKey: ["dashboard-harness"],
    queryFn: api.getAgentHarnessOverview,
  });

  const { data: riskDiscovery } = useQuery({
    queryKey: ["dashboard-risk-discovery"],
    queryFn: api.getGraphRiskDiscovery,
  });

  const exceptions = useMemo(() => exceptionsPage?.items || [], [exceptionsPage]);

  const openExceptions = useMemo(
    () => exceptions.filter((e: any) => !["APPROVED", "REJECTED"].includes(String(e.status).toUpperCase())),
    [exceptions]
  );

  const valueAtRisk = useMemo(
    () => sumDecimalStrings(openExceptions.map((e: any) => e.financial_exposure)),
    [openExceptions]
  );

  const avgResolutionHours = useMemo(() => {
    const resolved = exceptions.filter((e: any) => e.resolved_at && e.created_at);
    if (resolved.length === 0) return null;
    const totalHours = resolved.reduce((acc: number, e: any) => {
      const diff = new Date(e.resolved_at).getTime() - new Date(e.created_at).getTime();
      return acc + Math.max(0, diff / 3600000);
    }, 0);
    return Math.round(totalHours / resolved.length);
  }, [exceptions]);

  const ruleBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const ex of exceptions) {
      const rule = String(ex.rule_id || ex.type || "OTHER");
      counts[rule] = (counts[rule] || 0) + 1;
    }
    return Object.entries(counts)
      .map(([rule, count]) => ({ rule, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 6);
  }, [exceptions]);

  if (isLoading) {
    return (
      <div className="space-y-6" aria-label="Loading dashboard">
        <Skeleton className="h-36 w-full rounded-hero" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Skeleton className="h-72 lg:col-span-7" />
          <Skeleton className="h-72 lg:col-span-5" />
          <Skeleton className="h-64 lg:col-span-6" />
          <Skeleton className="h-64 lg:col-span-6" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-status-danger-fg/30 bg-status-danger-bg text-status-danger-fg text-sm">
        Failed to load dashboard metrics.
      </Card>
    );
  }

  const totalTx = data.kpis.transactions || 0;
  const matchedRateNum = totalTx > 0 ? Math.round((data.kpis.matched_cases / totalTx) * 100) : 0;
  const approvedCount = exceptions.filter((e: any) => String(e.status).toUpperCase() === "APPROVED").length;

  const funnelData = [
    { stage: "Documents", count: data.kpis.documents, fill: "var(--sand-400)" },
    { stage: "Evaluated", count: totalTx, fill: "var(--ink-700)" },
    { stage: "Matched", count: data.kpis.matched_cases, fill: "var(--status-success-fg)" },
    { stage: "Exceptions", count: data.kpis.open_exceptions, fill: "var(--status-danger-fg)" },
    { stage: "Approved", count: approvedCount, fill: "var(--status-warning-fg)" },
  ];

  const riskTimeline = [
    ...((riskDiscovery?.supplier_anomalies || []).slice(0, 3).map((a: any, i: number) => ({
      id: `anom-${i}`,
      title: a.vendor_name || "Vendor Pattern",
      detail: `${a.exception_count ?? a.count ?? 1} recurring discrepancy signals`,
      badge: "RISK_INDICATOR",
    }))),
    ...data.exception_queue.slice(0, 3).map((e) => ({
      id: e.id,
      title: e.type,
      detail: e.summary,
      badge: e.severity,
    })),
  ].slice(0, 5);

  const telemetry = harnessData?.gemini_telemetry;
  const aiProvider = data.ai_status?.configured_provider || "mock";
  const aiFallbackUsed = (data.ai_status?.fallback_count || 0) > 0 || (telemetry?.fallback_count || 0) > 0;
  const aiLatencyMs = telemetry?.avg_latency_ms ? `${Math.round(telemetry.avg_latency_ms)} ms` : "—";

  return (
    <div className="space-y-8">
      {/* Header Band */}
      <Card variant="hero">
        <PageCaption
          project="ReconX AI / Operations Console"
          module="Module / Finance Operations"
          index={`Active Tx / ${data.kpis.transactions}`}
        />
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="font-display text-3xl md:text-5xl font-bold text-ink-900">
              Finance Operations Dashboard
            </h1>
            <p className="text-sm md:text-base text-ink-700 mt-2 max-w-2xl">
              Three-way Purchase Order, Goods-Receipt &amp; Supplier Invoice reconciliation ledger.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/documents"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-control bg-ink-900 text-on-ink text-sm font-medium hover:-translate-y-px transition-transform shadow-hairline"
            >
              <span>Upload Documents</span>
              <ArrowUpRight className="w-4 h-4" />
            </Link>
            <Link
              to="/transactions"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-control border border-ink-900 text-ink-900 text-sm font-medium hover:bg-sand-100 transition-colors"
            >
              <span>View Transactions</span>
            </Link>
          </div>
        </div>
      </Card>

      {/* Hero Row: 4 Bento KPI Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
          <Card className="h-full flex flex-col justify-between gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                Auto-Match Rate
              </span>
              <Badge value={`${data.kpis.matched_cases}/${totalTx}`} tone="success" />
            </div>
            <div className="flex items-end justify-between gap-2">
              <div className="text-3xl font-bold text-status-success-fg">
                <AnimatedCount value={matchedRateNum} suffix="%" />
              </div>
              <MiniSparkline
                points={data.outcome_breakdown.map((o) => o.count)}
                color="var(--status-success-fg)"
              />
            </div>
            <div className="text-xs text-ink-500 flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5 text-status-success-fg" />
              <span>Deterministic 3-way match</span>
            </div>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
          <Card className="h-full flex flex-col justify-between gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                Open Exceptions
              </span>
              <Badge
                value={data.kpis.open_exceptions > 0 ? "Needs Action" : "Clear"}
                tone={data.kpis.open_exceptions > 0 ? "danger" : "success"}
              />
            </div>
            <div className="flex items-end justify-between gap-2">
              <div className="text-3xl font-bold text-status-danger-fg">
                <AnimatedCount value={data.kpis.open_exceptions} />
              </div>
              <MiniSparkline
                points={[0, data.kpis.pending_approvals, data.kpis.open_exceptions]}
                color="var(--status-danger-fg)"
              />
            </div>
            <div className="text-xs text-ink-500">
              {data.kpis.pending_approvals} awaiting maker-checker
            </div>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <Card className="h-full flex flex-col justify-between gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                Value at Risk
              </span>
              <Badge value="INR Exposure" tone="warning" />
            </div>
            <div className="flex items-end justify-between gap-2">
              <div className="font-mono tabular-nums text-2xl font-bold text-ink-900">
                {formatInrString(valueAtRisk)}
              </div>
              <MiniSparkline
                points={[0, openExceptions.length, data.kpis.open_exceptions]}
                color="var(--status-warning-fg)"
              />
            </div>
            <div className="text-xs text-ink-500">
              Sum of open exception exposure
            </div>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          <Card className="h-full flex flex-col justify-between gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                Avg Resolution Time
              </span>
              <Badge value={avgResolutionHours !== null ? "Measured" : "Pending"} tone="neutral" />
            </div>
            <div className="flex items-end justify-between gap-2">
              <div className="font-mono tabular-nums text-3xl font-bold text-ink-900">
                {avgResolutionHours !== null ? <AnimatedCount value={avgResolutionHours} suffix="h" /> : "—"}
              </div>
              <MiniSparkline points={[48, 36, avgResolutionHours ?? 24]} color="var(--ink-700)" />
            </div>
            <div className="text-xs text-ink-500 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>{data.kpis.documents} docs ingested</span>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Main Bento Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Large Card: Reconciliation Funnel */}
        <Card className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg font-bold text-ink-900">Reconciliation Funnel</h2>
              <p className="text-xs text-ink-500">
                Documents ingested through deterministic match, exceptions, and approval.
              </p>
            </div>
            <span className="text-[11px] uppercase tracking-[0.08em] text-ink-500 font-mono">
              Pipeline Flow
            </span>
          </div>
          {totalTx === 0 && data.kpis.documents === 0 ? (
            <EmptyState
              title="No Reconciliation Data Yet"
              description="Upload a PO, GRN, or Invoice document to populate the funnel."
              action={
                <Link to="/documents" className="text-xs font-semibold underline text-ink-900">
                  Go to Documents →
                </Link>
              }
            />
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnelData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                  <XAxis
                    dataKey="stage"
                    axisLine={{ stroke: chartTheme.gridStroke, strokeWidth: 1 }}
                    tickLine={false}
                    tick={chartTheme.axisTick}
                  />
                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    tick={chartTheme.axisTick}
                  />
                  <Tooltip content={<BentoChartTooltip />} cursor={{ fill: "var(--sand-100)" }} />
                  <Bar dataKey="count" radius={[8, 8, 0, 0]} maxBarSize={52}>
                    {funnelData.map((entry) => (
                      <Cell key={entry.stage} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Card: Exceptions by Rule (Horizontal Bar with Accent Gradient) */}
        <Card className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg font-bold text-ink-900">Exceptions by Rule</h2>
              <p className="text-xs text-ink-500">Quantity, price tolerance, and duplicate checks.</p>
            </div>
            <Link to="/exceptions" className="text-xs font-semibold text-ink-900 underline">
              Inspect
            </Link>
          </div>
          {ruleBreakdown.length === 0 ? (
            <EmptyState
              title="No Rule Exceptions"
              description="No deterministic rule failures recorded in this organization."
            />
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={ruleBreakdown}
                  layout="vertical"
                  margin={{ top: 4, right: 16, left: 12, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="ruleAccentGrad" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="var(--status-warning-fg)" stopOpacity={0.85} />
                      <stop offset="100%" stopColor="var(--status-danger-fg)" stopOpacity={0.95} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    type="number"
                    allowDecimals={false}
                    axisLine={{ stroke: chartTheme.gridStroke, strokeWidth: 1 }}
                    tickLine={false}
                    tick={chartTheme.axisTick}
                  />
                  <YAxis
                    type="category"
                    dataKey="rule"
                    width={92}
                    axisLine={false}
                    tickLine={false}
                    tick={chartTheme.axisTick}
                  />
                  <Tooltip content={<BentoChartTooltip />} cursor={{ fill: "var(--sand-100)" }} />
                  <Bar dataKey="count" fill="url(#ruleAccentGrad)" radius={[0, 6, 6, 0]} maxBarSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Card: Risk Indicators Timeline */}
        <Card className="lg:col-span-6 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-status-info-fg" aria-hidden="true" />
              <h2 className="font-display text-lg font-bold text-ink-900">Risk Indicators Timeline</h2>
            </div>
            <span className="text-[11px] font-medium text-status-info-fg bg-status-info-bg px-2.5 py-0.5 rounded-full">
              Risk indicators, not proof of fraud
            </span>
          </div>
          {riskTimeline.length === 0 ? (
            <EmptyState
              title="No Risk Indicators"
              description="No vendor anomaly or discrepancy signals flagged."
            />
          ) : (
            <ol className="relative border-l border-sand-200 ml-2 space-y-4 pl-5">
              {riskTimeline.map((item) => (
                <li key={item.id} className="relative">
                  <span
                    className="absolute -left-[25px] top-1.5 w-2.5 h-2.5 rounded-full bg-status-info-fg border-2 border-paper"
                    aria-hidden="true"
                  />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-ink-900 truncate">{item.title}</span>
                    <StatusPill value={item.badge} />
                  </div>
                  <p className="text-xs text-ink-500 mt-0.5 line-clamp-2">{item.detail}</p>
                </li>
              ))}
            </ol>
          )}
        </Card>

        {/* Card: Approval Queue with Maker-Checker & SLA Countdown */}
        <Card className="lg:col-span-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-lg font-bold text-ink-900">Approval Queue</h2>
              <p className="text-xs text-ink-500">Maker-checker governance &amp; 48h SLA countdown.</p>
            </div>
            <Link to="/exceptions" className="text-xs font-semibold text-ink-900 underline">
              View all
            </Link>
          </div>
          {openExceptions.length === 0 ? (
            <EmptyState
              title="Approval Queue Clear"
              description="All pending maker-checker exceptions have been resolved."
            />
          ) : (
            <ul className="divide-y divide-sand-200">
              {openExceptions.slice(0, 5).map((e: any) => {
                const sla = formatSlaCountdown(e.created_at);
                return (
                  <li key={e.id} className="py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        to={`/exceptions/${e.id}`}
                        className="text-sm font-semibold text-ink-900 hover:underline truncate block"
                      >
                        {e.exception_type || e.rule_id}
                      </Link>
                      <div className="text-xs text-ink-500 font-mono mt-0.5">
                        Exposure: {formatInrString(e.financial_exposure, e.currency)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge value={sla.label} tone={sla.urgent ? "danger" : "neutral"} />
                      <StatusPill value={e.status} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* Card: AI Status / Telemetry */}
        <Card variant="subtle" className="lg:col-span-12 flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
              <Sparkles className="w-3.5 h-3.5 text-ink-900" aria-hidden="true" />
              <span>AI Status &amp; Telemetry</span>
            </div>
            <h2 className="font-display text-xl font-bold text-ink-900">
              Gemini-Powered Financial Intelligence
            </h2>
            <p className="text-xs text-ink-700 max-w-2xl">
              LLMs assist contextual investigation summaries; deterministic matching and human maker-checker approvals govern all financial outcomes.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="px-3 py-2 rounded-control bg-paper border border-sand-200 font-mono">
              Provider: <strong className="uppercase text-ink-900">{aiProvider}</strong>
            </div>
            <div className="px-3 py-2 rounded-control bg-paper border border-sand-200 font-mono">
              Fallback Used:{" "}
              <strong className={aiFallbackUsed ? "text-status-warning-fg" : "text-status-success-fg"}>
                {aiFallbackUsed ? `YES (${data.ai_status?.fallback_count || telemetry?.fallback_count || 0})` : "NO"}
              </strong>
            </div>
            <div className="px-3 py-2 rounded-control bg-paper border border-sand-200 font-mono inline-flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-ink-500" />
              <span>Latency: <strong className="text-ink-900">{aiLatencyMs}</strong></span>
            </div>
            <Link
              to="/agent-harness"
              className="px-4 py-2 rounded-control border border-ink-900 text-ink-900 font-semibold hover:bg-paper transition-colors"
            >
              Open Agent Harness →
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};
