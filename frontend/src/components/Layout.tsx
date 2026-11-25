import React, { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Building2,
  ClipboardList,
  Cpu,
  FileText,
  GitCompare,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Network,
  Settings,
  ShieldCheck,
  Wallet,
  X,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";

export const Layout: React.FC = () => {
  const { user, hasPermission, logout } = useAuth();
  const qc = useQueryClient();
  const [notifOpen, setNotifOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [copilotResult, setCopilotResult] = useState<{
    answer: string;
    citations: { type: string; id: string; label: string }[];
    limitations: string;
  } | null>(null);

  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: api.listNotifications,
    refetchInterval: 15000,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const askCopilot = useMutation({
    mutationFn: (q: string) => api.copilotQuery(q),
    onSuccess: (res) => setCopilotResult(res),
  });

  const unreadCount = notifications.filter((n: any) => n.status === "UNREAD").length;

  const navItems = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, show: hasPermission("transactions:read") },
    { to: "/documents", label: "Documents", icon: FileText, show: hasPermission("documents:read") },
    { to: "/transactions", label: "Transactions", icon: GitCompare, show: hasPermission("transactions:read") },
    { to: "/exceptions", label: "Exceptions", icon: ClipboardList, show: hasPermission("exceptions:read") },
    { to: "/vendors", label: "Vendors", icon: Building2, show: hasPermission("vendors:read") },
    { to: "/cash", label: "Cash Obligations", icon: Wallet, show: hasPermission("transactions:read") },
    { to: "/audit", label: "Audit Explorer", icon: ShieldCheck, show: hasPermission("audit:read") },
    { to: "/admin", label: "Admin Settings", icon: Settings, show: hasPermission("admin:config:read") },
  ].filter((n) => n.show);

  const intelligenceItems = [
    { to: "/agent-harness", label: "Agent Harness", icon: Cpu, show: hasPermission("exceptions:read") },
    { to: "/obligation-graph", label: "Obligation Graph", icon: Network, show: hasPermission("transactions:read") },
  ].filter((n) => n.show);

  return (
    <div className="min-h-screen flex bg-slate-50">
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 z-40 md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}
      <aside
        className={`${
          mobileNavOpen ? "fixed inset-y-0 left-0 z-50 flex" : "hidden"
        } md:static md:flex w-60 bg-slate-900 text-slate-100 flex-col shrink-0`}
      >
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="min-w-0">
            <div className="text-lg font-bold tracking-tight">ReconX AI</div>
            <div className="text-xs text-slate-400 mt-0.5 truncate">{user?.organization_name}</div>
          </div>
          <button
            aria-label="Close navigation"
            onClick={() => setMobileNavOpen(false)}
            className="md:hidden p-1 text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMobileNavOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition ${
                    isActive ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800"
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
          {intelligenceItems.length > 0 && (
            <div className="pt-4">
              <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                INTELLIGENCE
              </div>
              {intelligenceItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileNavOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition ${
                        isActive
                          ? "bg-indigo-600 text-white"
                          : "text-slate-300 hover:bg-slate-800"
                      }`
                    }
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          )}
        </nav>
        <div className="p-4 border-t border-slate-800 text-xs">
          <div className="font-medium text-slate-200 truncate">{user?.full_name}</div>
          <div className="text-slate-400 truncate">{user?.roles.join(", ")}</div>
          <button
            onClick={() => logout()}
            className="mt-3 flex items-center gap-1.5 text-slate-300 hover:text-white"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-slate-200 px-4 md:px-6 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <button
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
              className="md:hidden p-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="hidden sm:block text-sm text-slate-500 truncate">
              Autonomous Three-Way Reconciliation • Deterministic Finance Engine
            </div>
          </div>
          <div className="flex items-center gap-3 relative">
            {hasPermission("copilot:read") && (
              <button
                onClick={() => setCopilotOpen(!copilotOpen)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <MessageSquare className="w-4 h-4 text-indigo-600" />
                <span>Finance Copilot</span>
              </button>
            )}
            <button
              aria-label="Notifications"
              onClick={() => setNotifOpen(!notifOpen)}
              className="relative p-2 rounded-lg border border-slate-200 hover:bg-slate-50"
            >
              <Bell className="w-4 h-4 text-slate-700" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-rose-600 text-white text-[10px] rounded-full px-1.5">
                  {unreadCount}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-12 w-80 bg-white border border-slate-200 rounded-xl shadow-lg z-40 p-3">
                <div className="text-xs font-semibold text-slate-700 mb-2">Notifications</div>
                {notifications.length === 0 ? (
                  <div className="text-xs text-slate-500 py-3">No notifications.</div>
                ) : (
                  <ul className="space-y-2 max-h-72 overflow-auto">
                    {notifications.map((n: any) => (
                      <li
                        key={n.id}
                        className={`p-2 rounded-lg text-xs border ${
                          n.status === "UNREAD" ? "bg-indigo-50 border-indigo-200" : "bg-slate-50 border-slate-200"
                        }`}
                      >
                        <div className="font-medium text-slate-800">{n.type}</div>
                        <div className="text-slate-600 mt-0.5">{n.message}</div>
                        {n.status === "UNREAD" && (
                          <button
                            onClick={() => markRead.mutate(n.id)}
                            className="mt-1 text-indigo-700 underline"
                          >
                            Mark read
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>

      {copilotOpen && (
        <aside className="w-96 bg-white border-l border-slate-200 flex flex-col p-4 shrink-0">
          <div className="flex items-center justify-between border-b pb-3">
            <div>
              <h2 className="font-semibold text-slate-900">Finance Copilot (Read-Only)</h2>
              <p className="text-xs text-slate-500">Org-scoped retrieval with record citations</p>
            </div>
            <button onClick={() => setCopilotOpen(false)} className="text-xs text-slate-500 hover:text-slate-800">
              Close
            </button>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim().length >= 2) askCopilot.mutate(question);
            }}
            className="mt-3 flex gap-2"
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about open exceptions, vendors..."
              className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
            />
            <button
              type="submit"
              disabled={askCopilot.isPending}
              className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
            >
              Ask
            </button>
          </form>
          <div className="mt-4 flex-1 overflow-auto space-y-3 text-sm">
            {askCopilot.isPending && <div className="text-slate-500">Retrieving authorized records...</div>}
            {copilotResult && (
              <div className="space-y-3">
                <div className="whitespace-pre-wrap bg-slate-50 border border-slate-200 rounded-lg p-3 text-slate-800">
                  {copilotResult.answer}
                </div>
                {copilotResult.citations.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1">Citations</div>
                    <div className="flex flex-wrap gap-1.5">
                      {copilotResult.citations.map((c, idx) => (
                        <Link
                          key={idx}
                          to={c.type === "vendor" ? `/vendors/${c.id}` : `/transactions/${c.id}`}
                          className="text-xs px-2 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100"
                        >
                          {c.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                <div className="text-[11px] text-slate-500">{copilotResult.limitations}</div>
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
};
