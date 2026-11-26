import React, { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Building2,
  ClipboardList,
  Command,
  Cpu,
  FileText,
  GitCompare,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  ShieldCheck,
  Sliders,
  Sparkles,
  Wallet,
  X,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";
import { ReconXMark } from "./brand/ReconXMark";
import { CommandPalette, StatusPill, ThemeToggle } from "./ui";
import { cn } from "../utils/cn";

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/documents": "Documents",
  "/transactions": "Transactions",
  "/exceptions": "Exceptions",
  "/vendors": "Vendors",
  "/cash": "Cash Obligations",
  "/audit": "Audit Explorer",
  "/admin": "Admin Settings",
  "/agent-harness": "Agent Harness",
  "/obligation-graph": "Obligation Graph",
  "/policy-studio": "Policy Studio",
  "/executive-brief": "Executive Brief",
};

export const Layout: React.FC = () => {
  const { user, hasPermission, logout } = useAuth();
  const qc = useQueryClient();
  const location = useLocation();
  const [notifOpen, setNotifOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [copilotResult, setCopilotResult] = useState<{
    answer: string;
    citations: { type: string; id: string; label: string }[];
    limitations: string;
  } | null>(null);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: api.listNotifications,
    refetchInterval: 15000,
  });

  const { data: dashData } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.dashboardSummary,
    staleTime: 30000,
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
  const llmStatus = (dashData as any)?.llm_status;

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
    { to: "/policy-studio", label: "Policy Studio", icon: Sliders, show: hasPermission("policies:read") },
    { to: "/executive-brief", label: "Executive Brief", icon: FileText, show: hasPermission("reports:read") },
  ].filter((n) => n.show);

  const currentCrumb =
    ROUTE_TITLES[location.pathname] ||
    (location.pathname.startsWith("/transactions/")
      ? "Three-Way Match Detail"
      : location.pathname.startsWith("/exceptions/")
        ? "Exception Detail"
        : location.pathname.startsWith("/vendors/")
          ? "Vendor Profile"
          : "Console");

  return (
    <div className="min-h-screen flex bg-canvas text-ink-900">
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-ink-900/40 z-40 lg:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <aside
        aria-label="Primary navigation"
        className={cn(
          mobileNavOpen ? "fixed inset-y-0 left-0 z-50 flex" : "hidden",
          "lg:static lg:flex flex-col shrink-0 bg-sand-100 border-r border-sand-200 transition-all duration-150",
          sidebarCollapsed ? "lg:w-20" : "w-[264px]"
        )}
      >
        <div className="p-5 border-b border-sand-200 flex items-center justify-between gap-2">
          <Link to="/" className="min-w-0 flex items-center gap-2">
            <ReconXMark variant={sidebarCollapsed ? "icon" : "full"} size="sm" />
          </Link>
          <button
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setSidebarCollapsed((c) => !c)}
            className="hidden lg:inline-flex p-1.5 rounded-control text-ink-500 hover:text-ink-900 hover:bg-sand-200/60"
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
          <button
            aria-label="Close navigation"
            onClick={() => setMobileNavOpen(false)}
            className="lg:hidden p-1.5 rounded-control text-ink-500 hover:text-ink-900"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {!sidebarCollapsed && user?.organization_name && (
          <div className="px-5 py-2.5 border-b border-sand-200 text-[11px] uppercase tracking-[0.08em] text-ink-500 truncate">
            {user.organization_name}
          </div>
        )}

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {!sidebarCollapsed && (
            <div className="px-3 pt-1 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
              Operations
            </div>
          )}
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMobileNavOpen(false)}
                title={sidebarCollapsed ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-control text-sm font-medium transition-colors duration-150",
                    isActive
                      ? "bg-ink-900 text-on-ink shadow-soft"
                      : "text-ink-700 hover:bg-sand-200/60 hover:text-ink-900",
                    sidebarCollapsed && "justify-center px-2"
                  )
                }
              >
                <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
              </NavLink>
            );
          })}

          {intelligenceItems.length > 0 && (
            <div className="pt-5">
              {!sidebarCollapsed && (
                <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                  Intelligence
                </div>
              )}
              <div className="space-y-1">
                {intelligenceItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileNavOpen(false)}
                      title={sidebarCollapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 px-3 py-2 rounded-control text-sm font-medium transition-colors duration-150",
                          isActive
                            ? "bg-ink-900 text-on-ink shadow-soft"
                            : "text-ink-700 hover:bg-sand-200/60 hover:text-ink-900",
                          sidebarCollapsed && "justify-center px-2"
                        )
                      }
                    >
                      <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                      {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          )}
        </nav>

        <div className="p-4 border-t border-sand-200 text-xs space-y-2">
          {!sidebarCollapsed && (
            <>
              <div className="font-semibold text-ink-900 truncate">{user?.full_name}</div>
              <div className="flex flex-wrap items-center gap-1.5">
                {(user?.roles || []).map((r) => (
                  <span
                    key={r}
                    className="px-2 py-0.5 rounded-full bg-sand-200 text-ink-700 text-[10px] font-semibold uppercase tracking-wider"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </>
          )}
          <button
            type="button"
            onClick={() => logout()}
            className={cn(
              "inline-flex items-center gap-2 text-ink-700 hover:text-ink-900 font-medium pt-1",
              sidebarCollapsed && "w-full justify-center"
            )}
          >
            <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
            {!sidebarCollapsed && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 bg-paper border-b border-sand-200 px-4 md:px-8 flex items-center justify-between gap-3 z-30">
          <div className="flex items-center gap-3 min-w-0">
            <button
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
              className="lg:hidden p-2 rounded-control border border-sand-200 text-ink-700 hover:bg-sand-100"
            >
              <Menu className="w-4 h-4" />
            </button>
            <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs text-ink-500 truncate">
              <span className="uppercase tracking-[0.08em] font-semibold">ReconX</span>
              <span aria-hidden="true">/</span>
              <span className="text-ink-900 font-medium truncate">{currentCrumb}</span>
            </nav>
          </div>

          <div className="flex items-center gap-2.5 relative">
            <button
              type="button"
              onClick={() => setCmdOpen(true)}
              aria-label="Open quick navigation"
              className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-control border border-sand-200 bg-sand-50 text-xs text-ink-500 hover:border-sand-400 hover:text-ink-900 transition-colors"
            >
              <Command className="w-3.5 h-3.5" />
              <span>Search</span>
              <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper border border-sand-200">
                ⌘K
              </kbd>
            </button>

            {llmStatus && (
              <Link
                to="/agent-harness"
                className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sand-100 border border-sand-200 text-[11px] font-medium text-ink-700 hover:border-sand-400"
              >
                <Sparkles className="w-3 h-3 text-ink-900" aria-hidden="true" />
                <span className="font-mono uppercase">{llmStatus.configured_provider || "mock"}</span>
                {llmStatus.last_fallback_used && (
                  <span className="text-status-warning-fg font-semibold">(fallback)</span>
                )}
              </Link>
            )}

            <ThemeToggle />

            {hasPermission("copilot:read") && (
              <button
                type="button"
                onClick={() => setCopilotOpen(!copilotOpen)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control border border-sand-200 bg-paper text-xs font-medium text-ink-900 hover:bg-sand-100 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Finance Copilot</span>
              </button>
            )}

            <button
              type="button"
              aria-label="Notifications"
              onClick={() => setNotifOpen(!notifOpen)}
              className="relative p-2 rounded-control border border-sand-200 bg-paper text-ink-700 hover:bg-sand-100 transition-colors"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-status-danger-fg text-paper text-[10px] font-mono rounded-full px-1.5">
                  {unreadCount}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-12 w-80 bg-paper border border-sand-200 rounded-card shadow-soft z-40 p-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 mb-3">
                  Notifications
                </div>
                {notifications.length === 0 ? (
                  <div className="text-xs text-ink-500 py-3">No notifications.</div>
                ) : (
                  <ul className="space-y-2 max-h-72 overflow-auto">
                    {notifications.map((n: any) => (
                      <li
                        key={n.id}
                        className={cn(
                          "p-3 rounded-control text-xs border",
                          n.status === "UNREAD"
                            ? "bg-sand-100 border-sand-400"
                            : "bg-sand-50 border-sand-200"
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-ink-900">{n.type}</span>
                          <StatusPill value={n.status} />
                        </div>
                        <div className="text-ink-700 mt-1">{n.message}</div>
                        {n.status === "UNREAD" && (
                          <button
                            type="button"
                            onClick={() => markRead.mutate(n.id)}
                            className="mt-1.5 text-ink-900 underline font-medium"
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

        <main className="flex-1 p-6 md:p-8 lg:p-10 overflow-auto max-w-[1440px] w-full mx-auto">
          <Outlet />
        </main>
      </div>

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />

      {copilotOpen && (
        <aside
          aria-label="Finance Copilot"
          className="w-96 bg-paper border-l border-sand-200 flex flex-col p-5 shrink-0 shadow-soft"
        >
          <div className="flex items-center justify-between border-b border-sand-200 pb-3">
            <div>
              <h2 className="font-display font-bold text-base text-ink-900">
                Finance Copilot (Read-Only)
              </h2>
              <p className="text-xs text-ink-500">
                Org-scoped retrieval with verified record citations
              </p>
            </div>
            <button
              type="button"
              onClick={() => setCopilotOpen(false)}
              className="text-xs text-ink-500 hover:text-ink-900"
            >
              Close
            </button>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim().length >= 2) askCopilot.mutate(question);
            }}
            className="mt-4 flex gap-2"
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about open exceptions, vendors..."
              className="flex-1 border border-sand-200 bg-sand-50 rounded-control px-3 py-2 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
            />
            <button
              type="submit"
              disabled={askCopilot.isPending}
              className="px-4 py-2 bg-ink-900 text-on-ink text-sm font-medium rounded-control hover:opacity-95"
            >
              Ask
            </button>
          </form>
          <div className="mt-4 flex-1 overflow-auto space-y-3 text-sm">
            {askCopilot.isPending && (
              <div className="text-xs text-ink-500">Retrieving authorized records...</div>
            )}
            {copilotResult && (
              <div className="space-y-3">
                <div className="whitespace-pre-wrap bg-sand-50 border border-sand-200 rounded-card p-3.5 text-sm text-ink-900">
                  {copilotResult.answer}
                </div>
                {copilotResult.citations.length > 0 && (
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 mb-1.5">
                      Citations
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {copilotResult.citations.map((c, idx) => (
                        <Link
                          key={idx}
                          to={c.type === "vendor" ? `/vendors/${c.id}` : `/transactions/${c.id}`}
                          className="font-mono text-xs px-2.5 py-1 rounded-full bg-sand-100 text-ink-900 border border-sand-200 hover:border-ink-900"
                        >
                          {c.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                <div className="text-[11px] text-ink-500">{copilotResult.limitations}</div>
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
};
