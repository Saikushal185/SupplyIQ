"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const navItems = [
  { href: "/dashboard" as Route, label: "Dashboard" },
  { href: "/analytics" as Route, label: "Analytics" },
  { href: "/forecast" as Route, label: "Forecast" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="rounded-3xl border border-white/10 bg-slate-900/80 p-5 shadow-glow backdrop-blur">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.25em] text-teal-300/80">SupplyIQ</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Control Tower</h1>
        <p className="mt-3 text-sm text-slate-300">
          Multi-layer supply intelligence for forecasting, analytics, and inventory actioning.
        </p>
      </div>

      <nav className="space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "flex rounded-2xl px-4 py-3 text-sm font-medium transition",
              pathname === item.href
                ? "bg-teal-400/20 text-white"
                : "text-slate-300 hover:bg-white/5 hover:text-white",
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
