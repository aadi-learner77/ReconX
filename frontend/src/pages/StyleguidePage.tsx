import React, { useState } from "react";
import { ReconXMark } from "../components/brand/ReconXMark";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  Input,
  PageCaption,
  SegmentedControl,
  Select,
  Skeleton,
  Stat,
  StatusPill,
  Stepper,
  Tabs,
  Textarea,
  ThemeToggle,
  Toggle,
} from "../components/ui";
import { formatInrString } from "../utils/money";

const SWATCHES = [
  { name: "--sand-50", cls: "bg-sand-50" },
  { name: "--sand-100", cls: "bg-sand-100" },
  { name: "--sand-200", cls: "bg-sand-200" },
  { name: "--sand-300", cls: "bg-sand-300" },
  { name: "--sand-400", cls: "bg-sand-400" },
  { name: "--paper", cls: "bg-paper" },
  { name: "--ink-900", cls: "bg-ink-900 text-on-ink" },
  { name: "--ink-700", cls: "bg-ink-700 text-on-ink" },
  { name: "--ink-500", cls: "bg-ink-500 text-on-ink" },
];

export const StyleguidePage: React.FC = () => {
  const [tab, setTab] = useState("tokens");
  const [seg, setSeg] = useState("pdf");
  const [toggleVal, setToggleVal] = useState(true);

  return (
    <div className="min-h-screen bg-canvas text-ink-900 p-8 md:p-12 space-y-10 max-w-6xl mx-auto">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex-1 min-w-[280px]">
          <PageCaption
            project="ReconX AI / Design System"
            module="Sandstone Ledger / Tokens & Components"
            index="Styleguide / v1.0"
          />
          <h1 className="font-display text-4xl font-bold text-ink-900">Sandstone Ledger</h1>
          <p className="text-sm text-ink-500 mt-1">
            Editorial design tokens, typography scale, brand marks, and accessible UI primitives.
          </p>
        </div>
        <ThemeToggle />
      </div>

      <Tabs
        value={tab}
        onChange={setTab}
        options={[
          { id: "tokens", label: "Tokens & Type" },
          { id: "components", label: "Components" },
        ]}
      />

      {tab === "tokens" ? (
        <div className="space-y-8">
          <Card variant="hero">
            <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500 mb-4">
              Brand Lockup Variants
            </div>
            <div className="flex flex-wrap items-center gap-8">
              <ReconXMark variant="full" size="lg" />
              <ReconXMark variant="icon" size="md" />
              <ReconXMark variant="mono-dark" size="md" />
              <div className="bg-ink-900 px-4 py-2 rounded-card">
                <ReconXMark variant="mono-light" size="sm" />
              </div>
            </div>
          </Card>

          <div className="grid grid-cols-3 md:grid-cols-9 gap-3">
            {SWATCHES.map((s) => (
              <div key={s.name} className="space-y-1.5">
                <div className={`h-14 rounded-card border border-sand-200 ${s.cls}`} />
                <div className="font-mono text-[11px] text-ink-700">{s.name}</div>
              </div>
            ))}
          </div>

          <Card>
            <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500 mb-4">
              Semantic Status Pills (WCAG AA)
            </div>
            <div className="flex flex-wrap gap-3">
              <StatusPill value="MATCHED" />
              <StatusPill value="REVIEW_REQUIRED" />
              <StatusPill value="EXCEPTION" />
              <StatusPill value="RISK_INDICATOR" />
              <StatusPill value="PENDING" />
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Stat label="Matched Rate" value="92.4%" tone="success" />
            <Stat label="Open Exposure" value={formatInrString("125000.00")} mono tone="danger" />
            <Stat label="Pending Approvals" value="3" tone="warning" />
            <Stat label="Processed Items" value="40" />
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          <Card className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <Button variant="primary">Primary Action</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="destructive">Destructive</Button>
            </div>
            <div className="flex flex-wrap items-center gap-6">
              <SegmentedControl
                value={seg}
                onChange={setSeg}
                options={[
                  { id: "pdf", label: "PDF" },
                  { id: "md", label: "Markdown" },
                  { id: "csv", label: "CSV" },
                ]}
              />
              <Toggle checked={toggleVal} onChange={setToggleVal} label="Enforce Maker-Checker" />
            </div>
            <Stepper
              activeId="match"
              steps={[
                { id: "doc", label: "DocumentAgent", state: "done" },
                { id: "match", label: "MatchingAgent", state: "running" },
                { id: "inv", label: "InvestigationAgent", state: "fallback" },
                { id: "audit", label: "AuditAgent", state: "idle" },
              ]}
            />
          </Card>

          <Card className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input label="Policy Key" defaultValue="POL-CUSTOM-002" />
            <Select label="Severity">
              <option>HIGH</option>
              <option>CRITICAL</option>
            </Select>
            <Textarea label="Rationale" rows={2} placeholder="Enter decision rationale..." />
          </Card>

          <DataTable
            rowKey={(r) => r.id}
            rows={[
              { id: "PO-2026-0001", vendor: "Bharat Precision", amount: "53100.00", status: "MATCHED" },
              { id: "PO-2026-0002", vendor: "Sahyadri Fasteners", amount: "14160.00", status: "EXCEPTION" },
            ]}
            columns={[
              { key: "id", header: "PO Number", mono: true, render: (r) => r.id },
              { key: "vendor", header: "Vendor", render: (r) => r.vendor },
              {
                key: "amount",
                header: "Exposure",
                align: "right",
                mono: true,
                render: (r) => formatInrString(r.amount),
              },
              { key: "status", header: "Status", render: (r) => <StatusPill value={r.status} /> },
            ]}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Skeleton className="h-32" />
            <EmptyState title="No Open Exceptions" description="All three-way obligations are reconciled." />
          </div>
        </div>
      )}
    </div>
  );
};
