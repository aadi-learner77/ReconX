import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Command as Cmdk } from "cmdk";
import { ArrowRight, FileText, Search } from "lucide-react";
import { api } from "../../api/client";
import { Modal } from "./Overlay";

export interface CommandItem {
  label: string;
  to: string;
  section: string;
}

const PAGE_COMMANDS: CommandItem[] = [
  { label: "Dashboard", to: "/", section: "Operations" },
  { label: "Reconciliations (Transactions)", to: "/transactions", section: "Operations" },
  { label: "Documents", to: "/documents", section: "Operations" },
  { label: "Exceptions", to: "/exceptions", section: "Operations" },
  { label: "Vendors", to: "/vendors", section: "Operations" },
  { label: "Cash Obligations", to: "/cash", section: "Operations" },
  { label: "Agent Harness", to: "/agent-harness", section: "Intelligence" },
  { label: "Obligation Graph", to: "/obligation-graph", section: "Intelligence" },
  { label: "Policy Studio", to: "/policy-studio", section: "Intelligence" },
  { label: "Executive Brief", to: "/executive-brief", section: "Intelligence" },
  { label: "Audit Trail", to: "/audit", section: "Governance" },
  { label: "Settings", to: "/admin", section: "Governance" },
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

  const { data: txData } = useQuery({
    queryKey: ["cmdk-tx", query],
    queryFn: () => api.listTransactions({ search: query, page_size: "6" }),
    enabled: open,
  });

  const go = (to: string) => {
    navigate(to);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Quick Navigation (⌘K)" maxWidthClass="max-w-lg">
      <Cmdk label="Global Command Menu" className="space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 text-ink-500 absolute left-3 top-2.5" strokeWidth={1.5} />
          <Cmdk.Input
            autoFocus
            value={query}
            onValueChange={setQuery}
            placeholder="Jump to pages, POs (PO-2026-0002), or vendors..."
            aria-label="Search pages, POs, or invoices"
            className="w-full rounded-control border border-sand-200 bg-sand-50 pl-9 pr-3 py-2 text-sm text-ink-900 focus:border-ink-900 focus:outline-none"
          />
        </div>

        <Cmdk.List className="max-h-72 overflow-y-auto rounded-card border border-sand-200 divide-y divide-sand-200">
          <Cmdk.Empty className="p-4 text-xs text-ink-500 text-center">
            No matching pages, POs, or invoices.
          </Cmdk.Empty>

          <Cmdk.Group
            heading="Pages"
            className="[&_[cmdk-group-heading]]:px-3.5 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-ink-500 [&_[cmdk-group-heading]]:bg-sand-100"
          >
            {PAGE_COMMANDS.map((item) => (
              <Cmdk.Item
                key={item.to}
                value={`${item.label} ${item.section}`}
                onSelect={() => go(item.to)}
                className="px-3.5 py-2.5 flex items-center justify-between text-sm cursor-pointer aria-selected:bg-sand-100 hover:bg-sand-100"
              >
                <div>
                  <div className="font-medium text-ink-900">{item.label}</div>
                  <div className="text-[11px] uppercase tracking-[0.08em] text-ink-500">
                    {item.section}
                  </div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-ink-500" strokeWidth={1.5} />
              </Cmdk.Item>
            ))}
          </Cmdk.Group>

          {(txData?.items || []).length > 0 && (
            <Cmdk.Group
              heading="Purchase Orders & Transactions"
              className="[&_[cmdk-group-heading]]:px-3.5 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:text-ink-500 [&_[cmdk-group-heading]]:bg-sand-100"
            >
              {(txData?.items || []).map((tx) => (
                <Cmdk.Item
                  key={tx.transaction_id}
                  value={`${tx.po_number || ""} ${tx.vendor_name} ${tx.transaction_id}`}
                  onSelect={() => go(`/transactions/${tx.transaction_id}`)}
                  className="px-3.5 py-2.5 flex items-center justify-between text-sm cursor-pointer aria-selected:bg-sand-100 hover:bg-sand-100"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileText className="w-3.5 h-3.5 text-ink-500 shrink-0" strokeWidth={1.5} />
                    <div className="min-w-0">
                      <div className="font-mono font-semibold text-ink-900 text-xs">
                        {tx.po_number || tx.transaction_id.slice(0, 8)}
                      </div>
                      <div className="text-xs text-ink-500 truncate">{tx.vendor_name}</div>
                    </div>
                  </div>
                  <span className="font-mono text-[11px] text-ink-700">{tx.latest_outcome || tx.status}</span>
                </Cmdk.Item>
              ))}
            </Cmdk.Group>
          )}
        </Cmdk.List>
      </Cmdk>
    </Modal>
  );
};
