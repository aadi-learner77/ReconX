import React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../../utils/cn";

export interface TabOption {
  id: string;
  label: string;
}

export const RadixTabs = TabsPrimitive.Root;

export const RadixTabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn("inline-flex border-b border-sand-200 gap-6", className)}
    {...props}
  />
));
RadixTabsList.displayName = "RadixTabsList";

export const RadixTabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "pb-2.5 text-sm font-medium border-b-2 -mb-px transition-colors text-ink-500 border-transparent hover:text-ink-900 data-[state=active]:border-ink-900 data-[state=active]:text-ink-900",
      className
    )}
    {...props}
  />
));
RadixTabsTrigger.displayName = "RadixTabsTrigger";

export const RadixTabsContent = TabsPrimitive.Content;

export const Tabs: React.FC<{
  options: TabOption[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}> = ({ options, value, onChange, className }) => (
  <div className={cn("inline-flex border-b border-sand-200 gap-6", className)} role="tablist">
    {options.map((opt) => {
      const active = opt.id === value;
      return (
        <button
          key={opt.id}
          role="tab"
          aria-selected={active}
          type="button"
          onClick={() => onChange(opt.id)}
          className={cn(
            "pb-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
            active
              ? "border-ink-900 text-ink-900"
              : "border-transparent text-ink-500 hover:text-ink-900"
          )}
        >
          {opt.label}
        </button>
      );
    })}
  </div>
);

export const SegmentedControl: React.FC<{
  options: TabOption[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}> = ({ options, value, onChange, className }) => (
  <div
    className={cn(
      "inline-flex items-center gap-1 rounded-control bg-sand-100 border border-sand-200 p-1",
      className
    )}
    role="group"
  >
    {options.map((opt) => {
      const active = opt.id === value;
      return (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          className={cn(
            "px-3 py-1.5 rounded-[7px] text-xs font-semibold transition-all",
            active
              ? "bg-ink-900 text-on-ink shadow-hairline"
              : "text-ink-700 hover:text-ink-900"
          )}
        >
          {opt.label}
        </button>
      );
    })}
  </div>
);

export const Toggle: React.FC<{
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}> = ({ checked, onChange, label }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    onClick={() => onChange(!checked)}
    className="inline-flex items-center gap-2.5 text-sm text-ink-900"
  >
    <span
      className={cn(
        "w-10 h-5 rounded-full border transition-colors relative inline-flex items-center px-0.5",
        checked ? "bg-ink-900 border-ink-900" : "bg-sand-200 border-sand-400"
      )}
    >
      <span
        className={cn(
          "w-3.5 h-3.5 rounded-full bg-paper transition-transform",
          checked ? "translate-x-5" : "translate-x-0"
        )}
      />
    </span>
    <span>{label}</span>
  </button>
);

export interface StepItem {
  id: string;
  label: string;
  state: "idle" | "running" | "done" | "fallback";
}

export const Stepper: React.FC<{
  steps: StepItem[];
  activeId?: string;
  onSelect?: (id: string) => void;
}> = ({ steps, activeId, onSelect }) => (
  <div className="flex flex-wrap items-center gap-2">
    {steps.map((step, idx) => {
      const isSelected = activeId === step.id;
      const dotClass =
        step.state === "done"
          ? "bg-status-success-fg"
          : step.state === "fallback"
            ? "bg-status-warning-fg"
            : step.state === "running"
              ? "bg-status-info-fg"
              : "bg-sand-400";
      return (
        <React.Fragment key={step.id}>
          <button
            type="button"
            onClick={onSelect ? () => onSelect(step.id) : undefined}
            className={cn(
              "inline-flex items-center gap-2 px-3 py-2 rounded-card border text-xs font-medium transition-all",
              isSelected
                ? "bg-ink-900 text-on-ink border-ink-900"
                : "bg-paper text-ink-900 border-sand-200 hover:border-sand-400"
            )}
          >
            <span className={cn("w-2 h-2 rounded-full shrink-0", dotClass)} />
            <span>{step.label}</span>
          </button>
          {idx < steps.length - 1 && (
            <span className="text-ink-500 text-xs select-none" aria-hidden="true">
              →
            </span>
          )}
        </React.Fragment>
      );
    })}
  </div>
);
