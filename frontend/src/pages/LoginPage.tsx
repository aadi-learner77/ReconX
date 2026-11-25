import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { ApiClientError } from "../api/client";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("operator@reconx-demo.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError("Login failed. Please verify backend connectivity.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl shadow-sm p-8">
        <div className="flex items-center gap-2.5 mb-6">
          <div className="p-2 rounded-xl bg-indigo-600 text-white">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">ReconX AI</h1>
            <p className="text-xs text-slate-500">Three-Way Invoice, PO & GRN Reconciliation</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-200">
          <div className="text-xs font-medium text-slate-500 mb-2">Seeded Role Accounts:</div>
          <div className="flex flex-wrap gap-1.5">
            {[
              "operator@reconx-demo.com",
              "approver@reconx-demo.com",
              "procurement@reconx-demo.com",
              "receiving@reconx-demo.com",
              "auditor@reconx-demo.com",
              "admin@reconx-demo.com",
            ].map((demoEmail) => (
              <button
                key={demoEmail}
                type="button"
                onClick={() => setEmail(demoEmail)}
                className="text-[11px] px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700"
              >
                {demoEmail.split("@")[0]}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
