import clsx from "clsx";
import type { ReactNode } from "react";

interface Column<T> {
  key: string;
  header: string;
  className?: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey?: (row: T, index: number) => string;
  emptyMessage?: string;
}

export function DataTable<T>({ rows, columns, rowKey, emptyMessage = "No records available." }: DataTableProps<T>) {
  return (
    <div className="overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/35">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-white/5">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={clsx("px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.24em] text-slate-400", column.className)}>
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {rows.length ? (
              rows.map((row, index) => (
                <tr key={rowKey ? rowKey(row, index) : String(index)} className="text-slate-200 transition hover:bg-white/5">
                  {columns.map((column) => (
                    <td key={column.key} className={clsx("px-4 py-4 align-top", column.className)}>
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-sm text-slate-400">
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
