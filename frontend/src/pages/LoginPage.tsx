import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { ApiClientError } from "../api/client";
import { ReconXMark } from "../components/brand/ReconXMark";
import { Button, Card, PageCaption, ThemeToggle } from "../components/ui";

const DEMO_ACCOUNTS = [
  "operator@reconx-demo.com",
  "approver@reconx-demo.com",
  "procurement@reconx-demo.com",
  "receiving@reconx-demo.com",
  "auditor@reconx-demo.com",
  "admin@reconx-demo.com",
];

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("operator@reconx-demo.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);

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
    <div className="min-h-screen bg-canvas text-ink-900 grid grid-cols-1 lg:grid-cols-12">
      {/* Left Sandstone Presentation Panel */}
      <div className="lg:col-span-6 bg-sand-300 p-8 md:p-12 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-sand-200">
        <div>
          <PageCaption
            project="ReconX AI / Identity Gate"
            module="Three-Way Match / Deterministic Ledger"
            index="Synchronise 2026 / PS-BA1"
          />
        </div>

        <div className="py-10 space-y-6">
          <ReconXMark variant="full" size="lg" />
          <h1 className="font-display text-3xl md:text-5xl font-bold text-ink-900 leading-[1.08] max-w-md">
            Autonomous three-way financial reconciliation.
          </h1>
          <p className="text-sm md:text-base text-ink-700 max-w-md">
            Deterministic PO, Goods-Receipt, and Invoice verification with evidence-grounded
            investigations and maker-checker governance.
          </p>
        </div>

        <div className="border-t border-ink-900/20 pt-4 flex flex-wrap items-center justify-between gap-2 text-[11px] uppercase tracking-[0.08em] text-ink-700">
          <span>Decimal Arithmetic • Zero Floating-Point</span>
          <span>AI Recommends • Humans Authorize</span>
        </div>
      </div>

      {/* Right Sign-In Form */}
      <div className="lg:col-span-6 flex items-center justify-center p-6 md:p-12 relative">
        <div className="absolute top-6 right-6">
          <ThemeToggle />
        </div>

        <Card className="max-w-md w-full p-8 space-y-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500 font-semibold">
              Authorized Access
            </div>
            <h2 className="font-display text-2xl font-bold text-ink-900 mt-1">Sign in to ReconX</h2>
          </div>

          {error && (
            <div className="p-3.5 rounded-control bg-status-danger-bg border border-status-danger-fg/30 text-sm text-status-danger-fg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block space-y-1.5 text-xs">
              <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                Email
              </span>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-control border border-sand-200 bg-sand-50 px-3.5 py-2.5 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
              />
            </label>
            <label className="block space-y-1.5 text-xs">
              <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                Password
              </span>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-control border border-sand-200 bg-sand-50 px-3.5 py-2.5 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
              />
            </label>
            <Button type="submit" disabled={busy} className="w-full py-2.5">
              {busy ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <div className="pt-4 border-t border-sand-200">
            <button
              type="button"
              onClick={() => setDemoOpen((o) => !o)}
              className="w-full flex items-center justify-between text-xs font-semibold uppercase tracking-[0.08em] text-ink-500 hover:text-ink-900"
            >
              <span>Demo access</span>
              {demoOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {demoOpen && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {DEMO_ACCOUNTS.map((demoEmail) => (
                  <button
                    key={demoEmail}
                    type="button"
                    onClick={() => setEmail(demoEmail)}
                    className="font-mono text-[11px] px-2.5 py-1 rounded-full bg-sand-100 border border-sand-200 hover:border-ink-900 text-ink-900 transition-colors"
                  >
                    {demoEmail.split("@")[0]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
