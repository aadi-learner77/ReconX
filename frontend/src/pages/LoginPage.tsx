import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../auth/AuthContext";
import { ApiClientError } from "../api/client";
import { ReconXMark } from "../components/brand/ReconXMark";
import { Button, Card, PageCaption, ThemeToggle, toast } from "../components/ui";

const DEMO_ACCOUNTS = [
  { role: "Operator", email: "operator@reconx-demo.com" },
  { role: "Approver", email: "approver@reconx-demo.com" },
  { role: "Procurement", email: "procurement@reconx-demo.com" },
  { role: "Receiving", email: "receiving@reconx-demo.com" },
  { role: "Auditor", email: "auditor@reconx-demo.com" },
  { role: "Admin", email: "admin@reconx-demo.com" },
];

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const passwordRef = useRef<HTMLInputElement | null>(null);
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
      toast.success("Signed in to ReconX");
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
    <main className="min-h-screen bg-canvas text-ink-900 grid grid-cols-1 lg:grid-cols-12">
      {/* Left Sandstone Brand Panel with Grain Gradient + Animated SVG Reconciliation Lines */}
      <div className="lg:col-span-6 bg-gradient-to-br from-sand-300 via-sand-200 to-sand-300 p-8 md:p-12 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-sand-200 relative overflow-hidden">
        <div>
          <PageCaption
            project="ReconX AI / Identity Gate"
            module="Three-Way Match / Deterministic Ledger"
            index="Synchronise 2026 / PS-BA1"
          />
        </div>

        <div className="py-8 space-y-6 relative z-10">
          <ReconXMark variant="full" size="lg" />
          <h1 className="font-display text-3xl md:text-5xl font-bold text-ink-900 leading-[1.08] max-w-md">
            Autonomous three-way financial reconciliation.
          </h1>
          <p className="text-sm md:text-base text-ink-700 max-w-md">
            Deterministic PO, Goods-Receipt, and Invoice verification with evidence-grounded
            investigations and maker-checker governance.
          </p>

          {/* Animated SVG Line Reconciliation Illustration */}
          <div className="pt-2 max-w-md">
            <svg
              viewBox="0 0 420 120"
              fill="none"
              className="w-full h-auto text-ink-900"
              aria-hidden="true"
            >
              {/* Connecting Animated Dashed Paths */}
              <motion.path
                d="M 68 60 L 166 28"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="4 4"
                initial={{ pathLength: 0, opacity: 0.3 }}
                animate={{ pathLength: 1, opacity: 0.85 }}
                transition={{ duration: 0.9, ease: "easeOut" }}
              />
              <motion.path
                d="M 68 60 L 166 92"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="4 4"
                initial={{ pathLength: 0, opacity: 0.3 }}
                animate={{ pathLength: 1, opacity: 0.85 }}
                transition={{ duration: 0.9, delay: 0.15, ease: "easeOut" }}
              />
              <motion.path
                d="M 248 28 L 336 60"
                stroke="var(--status-success-fg)"
                strokeWidth="2"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.8, delay: 0.35, ease: "easeOut" }}
              />
              <motion.path
                d="M 248 92 L 336 60"
                stroke="var(--status-warning-fg)"
                strokeWidth="2"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.8, delay: 0.45, ease: "easeOut" }}
              />

              {/* PO Node */}
              <rect x="8" y="42" width="60" height="36" rx="8" fill="var(--paper)" stroke="currentColor" strokeWidth="1.5" />
              <text x="38" y="64" textAnchor="middle" fill="currentColor" fontSize="11" fontFamily="JetBrains Mono, monospace" fontWeight="600">
                PO
              </text>

              {/* GRN Node */}
              <rect x="166" y="10" width="82" height="36" rx="8" fill="var(--paper)" stroke="var(--status-success-fg)" strokeWidth="1.5" />
              <text x="207" y="32" textAnchor="middle" fill="currentColor" fontSize="11" fontFamily="JetBrains Mono, monospace" fontWeight="600">
                GRN
              </text>

              {/* INV Node */}
              <rect x="166" y="74" width="82" height="36" rx="8" fill="var(--paper)" stroke="var(--status-warning-fg)" strokeWidth="1.5" />
              <text x="207" y="96" textAnchor="middle" fill="currentColor" fontSize="11" fontFamily="JetBrains Mono, monospace" fontWeight="600">
                INVOICE
              </text>

              {/* Match Engine Node */}
              <motion.circle
                cx="364"
                cy="60"
                r="26"
                fill="var(--ink-900)"
                initial={{ scale: 0.85, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.55, duration: 0.35 }}
              />
              <text x="364" y="64" textAnchor="middle" fill="var(--paper)" fontSize="10" fontFamily="JetBrains Mono, monospace" fontWeight="600">
                3-WAY
              </text>
            </svg>
          </div>
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
                ref={passwordRef}
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-control border border-sand-200 bg-sand-50 px-3.5 py-2.5 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
              />
            </label>
            <Button type="submit" loading={busy} className="w-full py-2.5">
              {busy ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          {/* Role-Labeled Demo-Account Quick-Fill Chips */}
          <div className="pt-4 border-t border-sand-200 space-y-2.5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
              Demo Account Quick-Fill
            </div>
            <div className="flex flex-wrap gap-1.5">
              {DEMO_ACCOUNTS.map((acct) => {
                const selected = email === acct.email;
                return (
                  <button
                    key={acct.email}
                    type="button"
                    onClick={() => {
                      setEmail(acct.email);
                      passwordRef.current?.focus();
                    }}
                    className={`font-mono text-[11px] px-2.5 py-1 rounded-full border transition-colors ${
                      selected
                        ? "bg-ink-900 text-on-ink border-ink-900"
                        : "bg-sand-100 border-sand-200 hover:border-ink-900 text-ink-900"
                    }`}
                  >
                    {acct.role}
                  </button>
                );
              })}
            </div>
          </div>
        </Card>
      </div>
    </main>
  );
};
