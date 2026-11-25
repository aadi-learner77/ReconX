import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export const CashViewPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["cash-obligations"],
    queryFn: api.cashObligations,
  });

  if (isLoading) return <div className="text-sm text-slate-500">Loading cash obligations...</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Cash Obligations</h1>
        <p className="text-sm text-slate-500">{data.note}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {data.buckets.map((b: any) => (
          <div key={b.bucket} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">{b.bucket}</div>
            <div className="text-xl font-bold font-mono mt-1">{b.amount}</div>
          </div>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Obligations by Vendor</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b">
              <th className="py-2">Vendor</th>
              <th className="py-2 text-right">Total Obligation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.by_vendor.map((v: any) => (
              <tr key={v.vendor}>
                <td className="py-2">{v.vendor}</td>
                <td className="py-2 text-right font-mono">{v.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
