import React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { Toaster as SonnerToaster, toast } from "sonner";
import { X } from "lucide-react";
import { cn } from "../../utils/cn";

export { toast };

export const Toaster: React.FC = () => (
  <SonnerToaster
    position="bottom-right"
    toastOptions={{
      classNames: {
        toast:
          "rounded-card border border-sand-200 bg-paper text-ink-900 shadow-floating font-sans text-sm",
        description: "text-xs text-ink-500",
        actionButton: "bg-ink-900 text-on-ink rounded-control text-xs font-medium px-2.5 py-1",
        cancelButton: "bg-sand-100 text-ink-700 rounded-control text-xs font-medium px-2.5 py-1",
      },
    }}
  />
);

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
}) => (
  <DialogPrimitive.Root open={open} onOpenChange={(next) => !next && onClose()}>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-ink-900/45 backdrop-blur-[1px]" />
      <DialogPrimitive.Content
        aria-describedby={undefined}
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-hero bg-paper border border-sand-200 p-6 shadow-floating space-y-4 animate-sandstone-enter",
          maxWidthClass
        )}
      >
        <div className="flex items-center justify-between gap-3 border-b border-sand-200 pb-3">
          <DialogPrimitive.Title className="font-display text-lg font-bold text-ink-900">
            {title}
          </DialogPrimitive.Title>
          <DialogPrimitive.Close asChild>
            <button
              type="button"
              aria-label="Close modal"
              className="p-1.5 rounded-control text-ink-500 hover:text-ink-900 hover:bg-sand-100"
            >
              <X className="w-4 h-4" />
            </button>
          </DialogPrimitive.Close>
        </div>
        <div className="text-sm text-ink-700">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 pt-2 border-t border-sand-200">{footer}</div>
        )}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>
);

export const Dialog = Modal;

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
}) => (
  <DialogPrimitive.Root open={open} onOpenChange={(next) => !next && onClose()}>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-ink-900/40 backdrop-blur-[1px]" />
      <DialogPrimitive.Content
        aria-describedby={undefined}
        className="fixed right-0 top-0 z-50 w-full max-w-md h-full bg-paper border-l border-sand-200 shadow-floating flex flex-col animate-sandstone-enter"
      >
        <div className="p-5 border-b border-sand-200 flex items-start justify-between gap-3">
          <div>
            <DialogPrimitive.Title className="font-display text-lg font-bold text-ink-900">
              {title}
            </DialogPrimitive.Title>
            {subtitle && <p className="text-xs text-ink-500 mt-0.5">{subtitle}</p>}
          </div>
          <DialogPrimitive.Close asChild>
            <button
              type="button"
              aria-label="Close drawer"
              className="p-1.5 rounded-control text-ink-500 hover:text-ink-900 hover:bg-sand-100"
            >
              <X className="w-4 h-4" />
            </button>
          </DialogPrimitive.Close>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>
);

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
        "px-4 py-3 rounded-card border text-sm flex items-center justify-between gap-3 shadow-card",
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
  <TooltipPrimitive.Provider delayDuration={150}>
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>
        <span className="inline-flex items-center">{children}</span>
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          sideOffset={6}
          className="z-50 rounded-control bg-ink-900 px-2.5 py-1 text-[11px] font-medium text-on-ink shadow-floating select-none"
        >
          {label}
          <TooltipPrimitive.Arrow className="fill-ink-900" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  </TooltipPrimitive.Provider>
);
