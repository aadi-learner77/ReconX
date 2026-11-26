import React, { useState } from "react";
import {
  AmountCell,
  Badge,
  Button,
  Card,
  CitationChip,
  ConfidenceMeter,
  DataTable,
  Dialog,
  Drawer,
  EmptyState,
  Input,
  PageCaption,
  RadixTabs,
  RadixTabsContent,
  RadixTabsList,
  RadixTabsTrigger,
  SegmentedControl,
  Select,
  Skeleton,
  Stat,
  StatusPill,
  Stepper,
  Tabs,
  ThemeToggle,
  Toggle,
  Tooltip,
  toast,
} from "../components/ui";
import { useTheme } from "../theme/ThemeContext";
import { formatInrString } from "../utils/money";

interface DemoRow {
  id: string;
  vendor: string;
  amount: string;
  variance: string | null;
  status: string;
  confidence: number;
}

const DEMO_ROWS: DemoRow[] = [
  {
    id: "PO-2026-0001",
    vendor: "Bharat Precision Components",
    amount: "53100.00",
    variance: null,
    status: "MATCHED",
    confidence: 0.98,
  },
  {
    id: "PO-2026-0002",
    vendor: "Sahyadri Industrial Fasteners",
    amount: "14160.00",
    variance: "1200.00",
    status: "EXCEPTION",
    confidence: 0.64,
  },
  {
    id: "PO-2026-0003",
    vendor: "Aravalli Metals & Alloys",
    amount: "125000.00",
    variance: "-450.00",
    status: "VARIANCE",
    confidence: 0.87,
  },
  {
    id: "PO-2026-0004",
    vendor: "Godavari Logistics & Freight",
    amount: "38400.00",
    variance: null,
    status: "NEEDS_REVIEW",
    confidence: 0.42,
  },
];

export const UiKitPage: React.FC = () => {
  const { theme } = useTheme();
  const [tab, setTab] = useState("overview");
  const [segment, setSegment] = useState("30d");
  const [toggleOn, setToggleOn] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loadingBtn, setLoadingBtn] = useState(false);

  return (
    <main className="min-h-screen bg-sand-50 text-ink-900">
      <div className="max-w-6xl mx-auto p-6 md:p-10 space-y-8">
        <PageCaption
          project="ReconX AI / Sandstone Ledger"
          module="Developer Route · /dev/ui-kit"
          index={`Theme: ${theme.toUpperCase()}`}
        />

        <Card variant="hero" className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-ink-900">
              ReconX UI Kit
            </h1>
            <p className="text-sm text-ink-700 mt-1">
              Radix-backed accessible primitives, decimal-safe money cells, and semantic status tokens in light &amp; dark modes.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button
              variant="primary"
              onClick={() =>
                toast.success("Sonner toast triggered", {
                  description: "Sandstone Ledger notification style active.",
                })
              }
            >
              Trigger Toast
            </Button>
          </div>
        </Card>

        {/* Buttons */}
        <Card className="space-y-4">
          <h2 className="font-display text-xl font-bold text-ink-900">Buttons</h2>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="danger">Danger</Button>
            <Button
              variant="primary"
              loading={loadingBtn}
              onClick={() => {
                setLoadingBtn(true);
                setTimeout(() => setLoadingBtn(false), 1200);
              }}
            >
              {loadingBtn ? "Processing..." : "Click for Loading"}
            </Button>
            <Button variant="primary" disabled>
              Disabled
            </Button>
          </div>
        </Card>

        {/* Badges & StatusPills */}
        <Card className="space-y-4">
          <h2 className="font-display text-xl font-bold text-ink-900">Badge / StatusPill</h2>
          <div className="flex flex-wrap items-center gap-2.5">
            <StatusPill value="MATCHED" />
            <StatusPill value="VARIANCE" />
            <StatusPill value="EXCEPTION" />
            <StatusPill value="NEEDS_REVIEW" />
            <StatusPill value="PENDING" />
            <Badge value="RISK_INDICATOR" />
            <Badge value="APPROVED" />
          </div>
        </Card>

        {/* Domain Primitives */}
        <Card className="space-y-5">
          <h2 className="font-display text-xl font-bold text-ink-900">
            Domain Primitives (ConfidenceMeter, CitationChip, AmountCell)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2.5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                ConfidenceMeter
              </div>
              <div className="flex flex-col gap-2">
                <ConfidenceMeter value={0.96} label="OCR" />
                <ConfidenceMeter value={0.65} label="Match" />
                <ConfidenceMeter value={0.32} label="Risk" />
              </div>
            </div>

            <div className="space-y-2.5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                CitationChip (click opens Evidence Drawer)
              </div>
              <div className="flex flex-wrap gap-2">
                <CitationChip
                  id="CIT-001"
                  evidence={{
                    citation_id: "CIT-001",
                    source_type: "PURCHASE_ORDER",
                    record_id: "PO-2026-0002",
                    field: "ordered_quantity",
                    observed_value: "100.0000",
                  }}
                />
                <CitationChip
                  id="CIT-002"
                  evidence={{
                    citation_id: "CIT-002",
                    source_type: "GOODS_RECEIPT",
                    record_id: "GRN-2026-0002",
                    field: "accepted_quantity",
                    observed_value: "90.0000",
                  }}
                />
                <CitationChip id="CIT-003" />
              </div>
            </div>

            <div className="space-y-2.5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                AmountCell (Indian Grouping + Delta)
              </div>
              <div className="flex items-start justify-between rounded-card border border-sand-200 p-3 bg-sand-50">
                <AmountCell amount="125000.00" />
                <AmountCell amount="14160.00" variance="1200.00" />
                <AmountCell amount="53100.00" variance="-450.00" />
              </div>
            </div>
          </div>
        </Card>

        {/* Stats & Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Stat label="Matched Volume" value={formatInrString("1425000.00")} mono tone="success" />
          <Stat label="Open Variance" value={formatInrString("48200.00")} mono tone="warning" />
          <Stat label="Exception Exposure" value={formatInrString("125000.00")} mono tone="danger" />
        </div>

        {/* DataTable */}
        <div className="space-y-3">
          <h2 className="font-display text-xl font-bold text-ink-900">
            DataTable (Sticky Header, Zebra Off, Density Toggle, Column Sort)
          </h2>
          <DataTable
            showDensityToggle
            rows={DEMO_ROWS}
            rowKey={(r) => r.id}
            onRowClick={(r) => toast.info(`Selected ${r.id}`, { description: r.vendor })}
            columns={[
              {
                key: "id",
                header: "PO Number",
                mono: true,
                sortable: true,
                sortValue: (r) => r.id,
                render: (r) => <span className="font-semibold">{r.id}</span>,
              },
              {
                key: "vendor",
                header: "Vendor",
                sortable: true,
                sortValue: (r) => r.vendor,
                render: (r) => r.vendor,
              },
              {
                key: "confidence",
                header: "Confidence",
                sortable: true,
                sortValue: (r) => r.confidence,
                render: (r) => <ConfidenceMeter value={r.confidence} segments={5} />,
              },
              {
                key: "amount",
                header: "Total / Delta",
                align: "right",
                mono: true,
                sortable: true,
                sortValue: (r) => Number(r.amount),
                render: (r) => <AmountCell amount={r.amount} variance={r.variance} />,
              },
              {
                key: "status",
                header: "Status",
                render: (r) => <StatusPill value={r.status} />,
              },
            ]}
          />
        </div>

        {/* Tabs, Controls, Tooltip, Dialog & Drawer */}
        <Card className="space-y-6">
          <h2 className="font-display text-xl font-bold text-ink-900">
            Radix Tabs, Tooltip, Dialog &amp; Drawer
          </h2>
          <Tabs
            value={tab}
            onChange={setTab}
            options={[
              { id: "overview", label: "Overview" },
              { id: "evidence", label: "Evidence" },
              { id: "audit", label: "Audit Trail" },
            ]}
          />

          <RadixTabs defaultValue="panel-a" className="space-y-3">
            <RadixTabsList>
              <RadixTabsTrigger value="panel-a">Composable Tab A</RadixTabsTrigger>
              <RadixTabsTrigger value="panel-b">Composable Tab B</RadixTabsTrigger>
            </RadixTabsList>
            <RadixTabsContent value="panel-a" className="text-xs text-ink-700">
              Built on @radix-ui/react-tabs with keyboard arrow navigation.
            </RadixTabsContent>
            <RadixTabsContent value="panel-b" className="text-xs text-ink-700">
              Second panel content rendered via Radix TabsContent.
            </RadixTabsContent>
          </RadixTabs>

          <div className="flex flex-wrap items-center gap-4">
            <SegmentedControl
              value={segment}
              onChange={setSegment}
              options={[
                { id: "30d", label: "30 Days" },
                { id: "60d", label: "60 Days" },
                { id: "90d", label: "90 Days" },
              ]}
            />
            <Toggle checked={toggleOn} onChange={setToggleOn} label="Strict Tolerance" />
            <Tooltip label="Tooltip powered by @radix-ui/react-tooltip">
              <Button variant="outline" size="sm">
                Hover for Tooltip
              </Button>
            </Tooltip>
            <Button variant="secondary" size="sm" onClick={() => setDialogOpen(true)}>
              Open Dialog
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setDrawerOpen(true)}>
              Open Drawer
            </Button>
          </div>

          <Stepper
            activeId="stage-2"
            steps={[
              { id: "stage-1", label: "DocumentAgent", state: "done" },
              { id: "stage-2", label: "MatchingAgent", state: "running" },
              { id: "stage-3", label: "RiskAgent", state: "fallback" },
              { id: "stage-4", label: "AuditAgent", state: "idle" },
            ]}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Vendor GSTIN" placeholder="29AABCB1234F1Z5" />
            <Select label="Reconciliation Rule">
              <option value="R-QTY-01">R-QTY-01 · Quantity Match</option>
              <option value="R-PRC-01">R-PRC-01 · Unit Price Tolerance</option>
            </Select>
          </div>
        </Card>

        {/* Skeleton Shimmer & EmptyState */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="space-y-3">
            <h2 className="font-display text-lg font-bold text-ink-900">Skeleton Shimmer</h2>
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-20 w-full" />
            <div className="grid grid-cols-3 gap-3">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          </Card>

          <EmptyState
            title="No Open Exceptions"
            description="All purchase orders, goods receipts, and invoices reconciled cleanly within deterministic tolerances."
            action={<Button variant="secondary" size="sm">Upload Document</Button>}
          />
        </div>
      </div>

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Radix Dialog Confirmation"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setDialogOpen(false);
                toast.success("Action confirmed");
              }}
            >
              Confirm
            </Button>
          </>
        }
      >
        Accessible modal dialog with focus trapping, Escape key handling, and backdrop click dismissal.
      </Dialog>

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Evidence Inspector Drawer"
        subtitle="Built on @radix-ui/react-dialog"
      >
        <p className="text-sm text-ink-700">
          Slide-over drawer for inspecting source documents, Neo4j graph nodes, or verified citation payloads.
        </p>
      </Drawer>
    </main>
  );
};
