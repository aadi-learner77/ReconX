import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export const VendorsPage: React.FC = () => {
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const { data: vendorsData } = useQuery({ queryKey: ["vendors"], queryFn: api.listVendors });

  const { data: profile } = useQuery({
    queryKey: ["vendor-profile", selectedVendorId],
    queryFn: () => api.getVendorProfile(selectedVendorId!),
    enabled: Boolean(selectedVendorId),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Vendor Intelligence</h1>
        <p className="text-sm text-slate-500">
          Historical performance metrics with disclosed date range and sample size N
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Suppliers</h2>
          <ul className="divide-y divide-slate-100">
            {(vendorsData?.items || []).map((v: any) => (
              <li key={v.id}>
                <button
                  onClick={() => setSelectedVendorId(v.id)}
                  className={`w-full text-left py-2.5 px-2 rounded-lg text-sm ${
                    selectedVendorId === v.id ? "bg-indigo-50 font-semibold" : "hover:bg-slate-50"
                  }`}
                >
                  <div>{v.legal_name}</div>
                  <div className="text-xs text-slate-500">{v.tax_identifier}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:col-span-8">
          {!profile ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-sm text-slate-500">
              Select a vendor to view profile, mismatch rate, and dispute history.
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">{profile.legal_name}</h2>
                  <p className="text-xs text-slate-500">
                    Window: {profile.date_range.from} to {profile.date_range.to} • Sample N=
                    {profile.transaction_count}
                  </p>
                </div>
                <StatusBadge value={profile.status} />
              </div>

              {profile.small_sample_warning && (
                <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
                  {profile.small_sample_warning}
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="p-3 rounded-lg bg-slate-50 border">
                  <div className="text-xs text-slate-500">Transactions (N)</div>
                  <div className="text-xl font-bold">{profile.transaction_count}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border">
                  <div className="text-xs text-slate-500">Mismatch Rate</div>
                  <div className="text-xl font-bold">{Math.round(profile.mismatch_rate * 100)}%</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border">
                  <div className="text-xs text-slate-500">Avg Delivery Days</div>
                  <div className="text-xl font-bold">{profile.avg_delivery_days ?? "—"}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border">
                  <div className="text-xs text-slate-500">Reliability Indicator</div>
                  <div className="text-xl font-bold">
                    {profile.reliability_indicator !== null
                      ? `${Math.round(profile.reliability_indicator * 100)}%`
                      : "N/A (small N)"}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
