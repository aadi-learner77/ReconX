import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card, DataTable, PageCaption, PageSkeleton, Stat } from "../components/ui";
import { formatInrString } from "../utils/money";

const BUCKET_LABELS: Record<string, string> = {
  OVERDUE: "Overdue",
  DUE_0_30: "Due 0–30 Days",
  DUE_31_60: "Due 31–60 Days",
  DUE_60_PLUS: "Due 61+ Days",
};

export const CashViewPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["cash-obligations"],
    queryFn: api.cashObligations,
  });

  if (isLoading) return <PageSkeleton />;
  if (!data) return null;

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Module / Cash Obligations" index="30 / 60 / 90-Day Aging" />
        <h1 className="font-display text-3xl font-bold text-ink-900">Cash Obligations</h1>
        <p className="text-sm text-ink-500 mt-1">{data.note}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {data.buckets.map((b: any) => (
          <Stat
            key={b.bucket}
            label={BUCKET_LABELS[b.bucket] || b.bucket}
            value={formatInrString(b.amount)}
            mono
            tone={b.bucket === "OVERDUE" ? "danger" : "default"}
          />
        ))}
      </div>

      {Array.isArray(data.forecast_30_60_90) && data.forecast_30_60_90.length > 0 && (
        <Card className="space-y-4">
          <div>
            <h2 className="font-display text-lg font-bold text-ink-900">
              30 / 60 / 90-Day Cash-Flow Projections
            </h2>
            {data.forecast_methodology && (
              <p className="text-xs text-ink-500 mt-0.5">{data.forecast_methodology}</p>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {data.forecast_30_60_90.map((f: any) => (
              <div
                key={f.horizon_days}
                className="p-4 rounded-card bg-sand-50 border border-sand-200 space-y-2"
              >
                <div className="text-[11px] font-semibold text-ink-500 uppercase tracking-[0.08em]">
                  {f.horizon_days}-Day Horizon
                </div>
                <div className="flex justify-between text-xs text-ink-700">
                  <span>Scheduled Obligations</span>
                  <span className="font-mono font-semibold text-ink-900">
                    {formatInrString(f.scheduled_amount)}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-ink-700">
                  <span>Projected Total</span>
                  <span className="font-mono font-bold text-ink-900">
                    {formatInrString(f.projected_total)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="space-y-3">
        <h2 className="font-display text-xl font-bold text-ink-900">Obligations by Vendor</h2>
        <DataTable
          rows={data.by_vendor}
          rowKey={(v: any) => v.vendor}
          columns={[
            { key: "vendor", header: "Vendor", render: (v: any) => v.vendor },
            {
              key: "amount",
              header: "Total Obligation",
              align: "right",
              mono: true,
              render: (v: any) => formatInrString(v.amount),
            },
          ]}
        />
      </div>
    </div>
  );
};
