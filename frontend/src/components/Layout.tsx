import React, { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
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
  Lock,
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
import { CommandPalette, Dialog, StatusPill, ThemeToggle, Tooltip } from "./ui";
import { cn } from "../utils/cn";

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/documents": "Documents",
  "/transactions": "Reconciliations",
  "/exceptions": "Exceptions",
  "/vendors": "Vendors",
  "/cash": "Cash Obligations",
  "/audit": "Audit Trail",
  "/admin": "Settings",
  "/agent-harness": "Agent Harness",
  "/obligation-graph": "Obligation Graph",
  "/policy-studio": "Policy Studio",
  "/executive-brief": "Executive Brief",
};

function getRoleDisplay(roles: string[]): { badge: string; approvalLimit: string } {
  const lower = roles.map((r) => r.toLowerCase());
  if (lower.some((r) => r.includes("admin"))) {
    return { badge: "Admin", approvalLimit: "Unlimited" };
  }
  if (lower.some((r) => r.includes("approver"))) {
    return { badge: "Approver", approvalLimit: "₹5,00,000" };
  }
  if (lower.some((r) => r.includes("auditor"))) {
    return { badge: "Auditor", approvalLimit: "Read-Only" };
  }
  return { badge: "Operator", approvalLimit: "₹0 (Maker)" };
}

interface NavDef {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number | string }>;
  allowed: boolean;
  requiredHint: string;
}

export const Layout: React.FC = () => {
  const { user, hasPermission, logout } = useAuth();
  const qc = useQueryClient();
  const location = useLocation();
  const navigate = useNavigate();
  const pendingG = useRef(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [copilotResult, setCopilotResult] = useState<{
    answer: string;
    citations: { type: string; id: string; label: string }[];
    limitations: string;
  } | null>(null);

  useEffect(() => {
    let gTimer: ReturnType<typeof setTimeout> | undefined;
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
        return;
      }
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "/") {
        e.preventDefault();
        setCmdOpen(true);
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        setShortcutsOpen((prev) => !prev);
        return;
      }
      if (e.key.toLowerCase() === "g" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        pendingG.current = true;
        clearTimeout(gTimer);
        gTimer = setTimeout(() => {
          pendingG.current = false;
        }, 900);
        return;
      }
      if (pendingG.current) {
        pendingG.current = false;
        if (e.key.toLowerCase() === "d") {
          e.preventDefault();
          navigate("/");
        } else if (e.key.toLowerCase() === "e") {
          e.preventDefault();
          navigate("/exceptions");
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      clearTimeout(gTimer);
    };
  }, [navigate]);

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
  const aiStatus = (dashData as any)?.ai_status;
  const isGeminiLive =
    aiStatus?.configured_provider === "gemini" &&
    aiStatus?.api_key_configured &&
    (aiStatus?.last_successful_provider === "gemini" || (aiStatus?.successful_calls || 0) > 0);
  const providerPillLabel = isGeminiLive
    ? "Gemini live"
    : aiStatus?.configured_provider === "gemini"
      ? "Gemini · fallback/idle"
      : "Mock · offline";

  const roleMeta = getRoleDisplay(user?.roles || []);

  const operationsNav: NavDef[] = [
    {
      to: "/",
      label: "Dashboard",
      icon: LayoutDashboard,
      allowed: hasPermission("transactions:read"),
      requiredHint: "Requires transactions:read",
    },
    {
      to: "/transactions",
      label: "Reconciliations",
      icon: GitCompare,
      allowed: hasPermission("transactions:read"),
      requiredHint: "Requires transactions:read",
    },
    {
      to: "/documents",
      label: "Documents",
      icon: FileText,
      allowed: hasPermission("documents:read"),
      requiredHint: "Requires documents:read",
    },
    {
      to: "/exceptions",
      label: "Exceptions",
      icon: ClipboardList,
      allowed: hasPermission("exceptions:read"),
      requiredHint: "Requires exceptions:read",
    },
    {
      to: "/vendors",
      label: "Vendors",
      icon: Building2,
      allowed: hasPermission("vendors:read"),
      requiredHint: "Requires vendors:read",
    },
    {
      to: "/cash",
      label: "Cash Obligations",
      icon: Wallet,
      allowed: hasPermission("transactions:read"),
      requiredHint: "Requires transactions:read",
    },
  ];

  const intelligenceNav: NavDef[] = [
    {
      to: "/agent-harness",
      label: "Agent Harness",
      icon: Cpu,
      allowed: hasPermission("exceptions:read"),
      requiredHint: "Requires exceptions:read",
    },
    {
      to: "/obligation-graph",
      label: "Obligation Graph",
      icon: Network,
      allowed: hasPermission("transactions:read"),
      requiredHint: "Requires transactions:read",
    },
    {
      to: "/policy-studio",
      label: "Policy Studio",
      icon: Sliders,
      allowed: hasPermission("policies:read"),
      requiredHint: "Requires policies:read permission",
    },
    {
      to: "/executive-brief",
      label: "Executive Brief",
      icon: FileText,
      allowed: hasPermission("reports:read"),
      requiredHint: "Requires reports:read permission",
    },
  ];

  const governanceNav: NavDef[] = [
    {
      to: "/audit",
      label: "Audit Trail",
      icon: ShieldCheck,
      allowed: hasPermission("audit:read"),
      requiredHint: "Requires Auditor or Admin role (audit:read)",
    },
    {
      to: "/admin",
      label: "Settings",
      icon: Settings,
      allowed: hasPermission("admin:config:read"),
      requiredHint: "Requires Admin role (admin:config:read)",
    },
  ];

  const currentCrumb =
    ROUTE_TITLES[location.pathname] ||
    (location.pathname.startsWith("/transactions/")
      ? "Three-Way Match Detail"
      : location.pathname.startsWith("/exceptions/")
        ? "Exception Detail"
        : location.pathname.startsWith("/vendors/")
          ? "Vendor Profile"
          : "Console");

  const renderGroup = (title: string, items: NavDef[]) => (
    <div className="pt-4 first:pt-0">
      {!sidebarCollapsed && (
        <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
          {title}
        </div>
      )}
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          if (!item.allowed) {
            return (
              <Tooltip key={item.to} label={item.requiredHint}>
                <span
                  aria-disabled="true"
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-control text-sm text-ink-500/60 cursor-not-allowed select-none",
                    sidebarCollapsed && "justify-center px-2"
                  )}
                >
                  <Icon className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
                  {!sidebarCollapsed && (
                    <>
                      <span className="truncate flex-1">{item.label}</span>
                      <Lock className="w-3 h-3 shrink-0 opacity-70" strokeWidth={1.5} />
                    </>
                  )}
                </span>
              </Tooltip>
            );
          }
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setMobileNavOpen(false)}
              title={sidebarCollapsed ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-control text-sm font-medium transition-colors duration-fast",
                  isActive
                    ? "bg-ink-900 text-on-ink shadow-hairline border-l-4 border-sand-300"
                    : "text-ink-700 hover:bg-sand-200/60 hover:text-ink-900",
                  sidebarCollapsed && "justify-center px-2 border-l-0"
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-canvas text-ink-900">
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-ink-900/45 z-40 lg:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      {/* Desktop Left Sidebar + Mobile Bottom Sheet */}
      <aside
        aria-label="Primary navigation"
        className={cn(
          mobileNavOpen
            ? "fixed inset-x-0 bottom-0 z-50 flex max-h-[82vh] rounded-t-hero border-t border-sand-200 shadow-floating"
            : "hidden",
          "lg:static lg:flex lg:max-h-none lg:rounded-none lg:border-t-0 lg:border-r lg:border-sand-200 flex-col shrink-0 bg-sand-100 transition-all duration-base",
          sidebarCollapsed ? "lg:w-20" : "lg:w-[264px]"
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
              <PanelLeftOpen className="w-4 h-4" strokeWidth={1.5} />
            ) : (
              <PanelLeftClose className="w-4 h-4" strokeWidth={1.5} />
            )}
          </button>
          <button
            aria-label="Close navigation"
            onClick={() => setMobileNavOpen(false)}
            className="lg:hidden p-1.5 rounded-control text-ink-500 hover:text-ink-900"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {!sidebarCollapsed && user?.organization_name && (
          <div className="px-5 py-2.5 border-b border-sand-200 text-[11px] uppercase tracking-[0.08em] text-ink-500 truncate">
            {user.organization_name}
          </div>
        )}

        <nav className="flex-1 p-3 space-y-2 overflow-y-auto">
          {renderGroup("Operations", operationsNav)}
          {renderGroup("Intelligence", intelligenceNav)}
          {renderGroup("Governance", governanceNav)}
        </nav>

        <div className="p-4 border-t border-sand-200 text-xs space-y-2">
          {!sidebarCollapsed && (
            <div className="space-y-1">
              <div className="font-semibold text-ink-900 truncate">{user?.full_name}</div>
              <div className="font-mono text-[11px] text-ink-500">
                {roleMeta.badge} • Limit {roleMeta.approvalLimit}
              </div>
            </div>
          )}
          <button
            type="button"
            onClick={() => logout()}
            className={cn(
              "inline-flex items-center gap-2 text-ink-700 hover:text-ink-900 font-medium pt-1",
              sidebarCollapsed && "w-full justify-center"
            )}
          >
            <LogOut className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
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
              <Menu className="w-4 h-4" strokeWidth={1.5} />
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
              <Command className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span>Search</span>
              <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper border border-sand-200">
                ⌘K
              </kbd>
            </button>

            {/* Honest AI Provider Status Strip */}
            <Link
              to="/agent-harness"
              title="View LLM telemetry and Agent Harness"
              className={cn(
                "hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium transition-colors",
                isGeminiLive
                  ? "bg-status-success-bg border-status-success-fg/30 text-status-success-fg"
                  : "bg-sand-100 border-sand-200 text-ink-700"
              )}
            >
              <Sparkles className="w-3 h-3" strokeWidth={1.5} aria-hidden="true" />
              <span className="font-mono">{providerPillLabel}</span>
            </Link>

            <ThemeToggle />

            {hasPermission("copilot:read") && (
              <button
                type="button"
                onClick={() => setCopilotOpen(!copilotOpen)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control border border-sand-200 bg-paper text-xs font-medium text-ink-900 hover:bg-sand-100 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
                <span className="hidden sm:inline">Finance Copilot</span>
              </button>
            )}

            <button
              type="button"
              aria-label="Notifications"
              onClick={() => setNotifOpen(!notifOpen)}
              className="relative p-2 rounded-control border border-sand-200 bg-paper text-ink-700 hover:bg-sand-100 transition-colors"
            >
              <Bell className="w-4 h-4" strokeWidth={1.5} />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-status-danger-fg text-paper text-[10px] font-mono rounded-full px-1.5">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* User Chip with Role Badge & Mono Approval Limit */}
            {user && (
              <div className="hidden xl:flex items-center gap-2 pl-2 border-l border-sand-200 text-xs">
                <span className="px-2 py-0.5 rounded-full bg-sand-100 border border-sand-200 font-semibold text-ink-900">
                  {roleMeta.badge}
                </span>
                <span className="font-mono text-[11px] text-ink-500">
                  {roleMeta.approvalLimit}
                </span>
              </div>
            )}

            {notifOpen && (
              <div className="absolute right-0 top-12 w-80 bg-paper border border-sand-200 rounded-card shadow-floating z-40 p-4">
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
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />

      <Dialog
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
        title="Keyboard Shortcuts"
        maxWidthClass="max-w-md"
      >
        <div className="space-y-2.5 text-xs">
          {[
            { keys: "Ctrl / Cmd + K", desc: "Open Command Palette" },
            { keys: "/", desc: "Focus Global Search" },
            { keys: "g then d", desc: "Go to Dashboard" },
            { keys: "g then e", desc: "Go to Exceptions" },
            { keys: "?", desc: "Toggle Keyboard Shortcuts" },
          ].map((s) => (
            <div
              key={s.keys}
              className="flex items-center justify-between py-1.5 border-b border-sand-200 last:border-b-0"
            >
              <span className="text-ink-700">{s.desc}</span>
              <kbd className="font-mono text-[11px] px-2 py-0.5 rounded bg-sand-100 border border-sand-200 text-ink-900">
                {s.keys}
              </kbd>
            </div>
          ))}
        </div>
      </Dialog>

      {copilotOpen && (
        <aside
          aria-label="Finance Copilot"
          className="w-96 bg-paper border-l border-sand-200 flex flex-col p-5 shrink-0 shadow-card"
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
