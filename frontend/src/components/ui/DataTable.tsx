import React, { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Rows3 } from "lucide-react";
import { cn } from "../../utils/cn";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  mono?: boolean;
  sortable?: boolean;
  sortValue?: (row: T) => string | number;
  render: (row: T) => React.ReactNode;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T, idx: number) => string;
  onRowClick?: (row: T) => void;
  empty?: React.ReactNode;
  showDensityToggle?: boolean;
  defaultDensity?: "comfortable" | "compact";
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  empty,
  showDensityToggle = false,
  defaultDensity = "comfortable",
  className,
}: DataTableProps<T>) {
  const [density, setDensity] = useState<"comfortable" | "compact">(defaultDensity);
  const [sortState, setSortState] = useState<{ key: string; dir: "asc" | "desc" } | null>(null);

  const sortedRows = useMemo(() => {
    if (!sortState) return rows;
    const col = columns.find((c) => c.key === sortState.key);
    if (!col?.sortValue) return rows;
    const getter = col.sortValue;
    return [...rows].sort((a, b) => {
      const av = getter(a);
      const bv = getter(b);
      if (av === bv) return 0;
      const cmp = typeof av === "number" && typeof bv === "number"
        ? av - bv
        : String(av).localeCompare(String(bv), undefined, { numeric: true });
      return sortState.dir === "asc" ? cmp : -cmp;
    });
  }, [rows, columns, sortState]);

  if (rows.length === 0 && empty) {
    return <>{empty}</>;
  }

  const toggleSort = (key: string) => {
    setSortState((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "asc" };
      if (prev.dir === "asc") return { key, dir: "desc" };
      return null;
    });
  };

  const cellPad = density === "compact" ? "py-2 px-3" : "py-3 px-4";

  return (
    <div className={cn("overflow-x-auto rounded-card border border-sand-200 bg-paper shadow-card", className)}>
      {showDensityToggle && (
        <div className="flex items-center justify-end gap-2 px-3 py-2 border-b border-sand-200 bg-sand-50/70">
          <button
            type="button"
            onClick={() => setDensity((d) => (d === "comfortable" ? "compact" : "comfortable"))}
            className="inline-flex items-center gap-1.5 text-[11px] font-medium text-ink-700 hover:text-ink-900 px-2 py-1 rounded-control border border-sand-200 bg-paper transition-colors"
          >
            <Rows3 className="w-3.5 h-3.5" />
            <span>Density: {density === "comfortable" ? "Comfortable" : "Compact"}</span>
          </button>
        </div>
      )}
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 bg-paper z-10 border-b border-sand-200">
          <tr>
            {columns.map((col) => {
              const isSortable = Boolean(col.sortable && col.sortValue);
              const activeSort = sortState?.key === col.key ? sortState.dir : null;
              return (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    cellPad,
                    "text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500 whitespace-nowrap select-none",
                    col.align === "right"
                      ? "text-right"
                      : col.align === "center"
                        ? "text-center"
                        : "text-left"
                  )}
                >
                  {isSortable ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(col.key)}
                      className={cn(
                        "inline-flex items-center gap-1 hover:text-ink-900 transition-colors",
                        col.align === "right" && "flex-row-reverse"
                      )}
                    >
                      <span>{col.header}</span>
                      {activeSort === "asc" ? (
                        <ArrowUp className="w-3 h-3 text-ink-900" />
                      ) : activeSort === "desc" ? (
                        <ArrowDown className="w-3 h-3 text-ink-900" />
                      ) : (
                        <ArrowUpDown className="w-3 h-3 opacity-45" />
                      )}
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-sand-200">
          {sortedRows.map((row, idx) => (
            <tr
              key={rowKey(row, idx)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                "bg-paper transition-colors hover:bg-sand-100/75",
                onRowClick && "cursor-pointer"
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    cellPad,
                    "text-ink-900",
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
