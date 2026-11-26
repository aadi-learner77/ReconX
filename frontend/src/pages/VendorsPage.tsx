import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Card, EmptyState, PageCaption, Stat, StatusPill } from "../components/ui";

export const VendorsPage: React.FC = () => {
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const { data: vendorsData } = useQuery({ queryKey: ["vendors"], queryFn: api.listVendors });

  const { data: profile } = useQuery({
    queryKey: ["vendor-profile", selectedVendorId],
    queryFn: () => api.getVendorProfile(selectedVendorId!),
    enabled: Boolean(selectedVendorId),
  });

  return (
    <div className="space-y-8">
      <div>
        <PageCaption module="Module / Vendor Intelligence" index="Small-Sample Guarded" />
        <h1 className="font-display text-3xl font-bold text-ink-900">Vendor Intelligence</h1>
        <p className="text-sm text-ink-500 mt-1">
          Historical performance metrics with disclosed date range and sample size N
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Card className="lg:col-span-4">
          <h2 className="font-display text-base font-bold text-ink-900 mb-3">Suppliers</h2>
          <ul className="divide-y divide-sand-200">
            {(vendorsData?.items || []).map((v: any) => (
              <li key={v.id}>
                <button
                  onClick={() => setSelectedVendorId(v.id)}
                  className={`w-full text-left py-3 px-2.5 rounded-control text-sm transition-colors ${
                    selectedVendorId === v.id ? "bg-sand-100 font-semibold" : "hover:bg-sand-50"
                  }`}
                >
                  <div className="text-ink-900">{v.legal_name}</div>
                  <div className="text-xs font-mono text-ink-500 mt-0.5">{v.tax_identifier}</div>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <div className="lg:col-span-8">
          {!profile ? (
            <EmptyState
              title="Select a supplier"
              description="Choose a supplier from the left list to view mismatch rate, delivery timeliness, and dispute history."
            />
          ) : (
            <Card className="space-y-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="font-display text-2xl font-bold text-ink-900">
                    {profile.legal_name}
                  </h2>
                  <p className="text-xs font-mono text-ink-500 mt-0.5">
                    Window: {profile.date_range.from} to {profile.date_range.to} • Sample N=
                    {profile.transaction_count}
                  </p>
                </div>
                <StatusPill value={profile.status} />
              </div>

              {profile.small_sample_warning && (
                <div className="p-3.5 rounded-control bg-status-warning-bg border border-status-warning-fg/30 text-xs text-status-warning-fg font-medium">
                  {profile.small_sample_warning}
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat label="Transactions (N)" value={profile.transaction_count} className="p-4" />
                <Stat
                  label="Mismatch Rate"
                  value={`${Math.round(profile.mismatch_rate * 100)}%`}
                  mono
                  className="p-4"
                />
                <Stat
                  label="Delivery Timeliness (Avg Days)"
                  value={profile.avg_delivery_days ?? "—"}
                  mono
                  className="p-4"
                />
                <Stat
                  label="Reliability Indicator"
                  value={profile.reliability_score ?? "N/A (small N)"}
                  className="p-4"
                />
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
