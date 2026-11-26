import React from "react";
import { cn } from "../../utils/cn";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  mono?: boolean;
  render: (row: T) => React.ReactNode;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T, idx: number) => string;
  onRowClick?: (row: T) => void;
  empty?: React.ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  empty,
  className,
}: DataTableProps<T>) {
  if (rows.length === 0 && empty) {
    return <>{empty}</>;
  }

  return (
    <div className={cn("overflow-x-auto rounded-card border border-sand-200 bg-paper", className)}>
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 bg-paper z-10 border-b border-sand-200">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  "py-3 px-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 whitespace-nowrap",
                  col.align === "right"
                    ? "text-right"
                    : col.align === "center"
                      ? "text-center"
                      : "text-left"
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-sand-200">
          {rows.map((row, idx) => (
            <tr
              key={rowKey(row, idx)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                "odd:bg-paper even:bg-sand-100/60 transition-colors",
                onRowClick && "cursor-pointer hover:bg-sand-100"
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    "py-3 px-4 text-ink-900",
                    col.align === "right"
                      ? "text-right"
                      : col.align === "center"
                        ? "text-center"
                        : "text-left",
                    col.mono && "font-mono tabular-nums text-xs"
                  )}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
