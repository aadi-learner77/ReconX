import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../../utils/cn";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidthClass?: string;
}

export const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  title,
  children,
  footer,
  maxWidthClass = "max-w-lg",
}) => {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className={cn(
          "w-full rounded-hero bg-paper border border-sand-200 p-6 shadow-soft space-y-4 animate-sandstone-enter",
          maxWidthClass
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-sand-200 pb-3">
          <h3 className="font-display text-lg font-bold text-ink-900">{title}</h3>
          <button
            type="button"
            aria-label="Close modal"
            onClick={onClose}
            className="p-1.5 rounded-control text-ink-500 hover:text-ink-900 hover:bg-sand-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="text-sm text-ink-700">{children}</div>
        {footer && <div className="flex justify-end gap-2 pt-2 border-t border-sand-200">{footer}</div>}
      </div>
    </div>
  );
};

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export const Drawer: React.FC<DrawerProps> = ({
  open,
  onClose,
  title,
  subtitle,
  children,
}) => {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-ink-900/40"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md h-full bg-paper border-l border-sand-200 shadow-soft flex flex-col animate-sandstone-enter"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-sand-200 flex items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-lg font-bold text-ink-900">{title}</h3>
            {subtitle && <p className="text-xs text-ink-500 mt-0.5">{subtitle}</p>}
          </div>
          <button
            type="button"
            aria-label="Close drawer"
            onClick={onClose}
            className="p-1.5 rounded-control text-ink-500 hover:text-ink-900 hover:bg-sand-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
};

export interface ToastProps {
  message: string;
  tone?: "info" | "success" | "warning" | "danger";
  onDismiss?: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, tone = "info", onDismiss }) => {
  const toneClasses =
    tone === "success"
      ? "bg-status-success-bg text-status-success-fg border-status-success-fg/30"
      : tone === "warning"
        ? "bg-status-warning-bg text-status-warning-fg border-status-warning-fg/30"
        : tone === "danger"
          ? "bg-status-danger-bg text-status-danger-fg border-status-danger-fg/30"
          : "bg-sand-100 text-ink-900 border-sand-200";

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "px-4 py-3 rounded-card border text-sm flex items-center justify-between gap-3 shadow-soft",
        toneClasses
      )}
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs underline opacity-80 hover:opacity-100 shrink-0"
        >
          Dismiss
        </button>
      )}
    </div>
  );
};

export interface TooltipProps {
  label: string;
  children: React.ReactNode;
}

export const Tooltip: React.FC<TooltipProps> = ({ label, children }) => (
  <span className="relative group inline-flex items-center">
    {children}
    <span
      role="tooltip"
      className="pointer-events-none opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1 rounded-control bg-ink-900 text-on-ink text-[11px] whitespace-nowrap z-40 shadow-soft"
    >
      {label}
    </span>
  </span>
);
