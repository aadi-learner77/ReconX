import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ArrowRight } from "lucide-react";
import { Modal } from "./Overlay";

export interface CommandItem {
  label: string;
  to: string;
  section: string;
}

const DEFAULT_COMMANDS: CommandItem[] = [
  { label: "Dashboard Overview", to: "/", section: "Core" },
  { label: "Document Workspace", to: "/documents", section: "Core" },
  { label: "Transactions Ledger", to: "/transactions", section: "Core" },
  { label: "Exceptions Queue", to: "/exceptions", section: "Core" },
  { label: "Vendor Intelligence", to: "/vendors", section: "Core" },
  { label: "Cash Obligations", to: "/cash", section: "Core" },
  { label: "Agent Harness Explorer", to: "/agent-harness", section: "Intelligence" },
  { label: "Financial Obligation Graph", to: "/obligation-graph", section: "Intelligence" },
  { label: "Policy Studio", to: "/policy-studio", section: "Intelligence" },
  { label: "Executive Boardroom Brief", to: "/executive-brief", section: "Intelligence" },
  { label: "Audit Explorer", to: "/audit", section: "Governance" },
  { label: "Admin Settings", to: "/admin", section: "Governance" },
];

export const CommandPalette: React.FC<{
  open: boolean;
  onClose: () => void;
}> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return DEFAULT_COMMANDS;
    return DEFAULT_COMMANDS.filter(
      (c) => c.label.toLowerCase().includes(q) || c.section.toLowerCase().includes(q)
    );
  }, [query]);

  return (
    <Modal open={open} onClose={onClose} title="Quick Navigation" maxWidthClass="max-w-md">
      <div className="space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 text-ink-500 absolute left-3 top-2.5" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Jump to page or module..."
            aria-label="Search pages"
            className="w-full rounded-control border border-sand-200 bg-sand-50 pl-9 pr-3 py-2 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
          />
        </div>
        <ul className="max-h-64 overflow-y-auto divide-y divide-sand-200 rounded-card border border-sand-200">
          {filtered.length === 0 ? (
            <li className="p-4 text-xs text-ink-500 text-center">No matching destinations.</li>
          ) : (
            filtered.map((item) => (
              <li key={item.to}>
                <button
                  type="button"
                  onClick={() => {
                    navigate(item.to);
                    onClose();
                  }}
                  className="w-full px-3.5 py-2.5 text-left flex items-center justify-between text-sm hover:bg-sand-100 transition-colors"
                >
                  <div>
                    <div className="font-medium text-ink-900">{item.label}</div>
                    <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                      {item.section}
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-ink-500" />
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </Modal>
  );
};
