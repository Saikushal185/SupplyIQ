"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Activity, BarChart3, BrainCircuit, ShieldCheck } from "lucide-react";

import { useSessionContext } from "@/context/session-context";

interface NavItem {
  href: Route;
  label: string;
  icon: typeof Activity;
  visible: (canViewForecast: boolean) => boolean;
}

const navItems: NavItem[] = [
  { href: "/dashboard" as Route, label: "Dashboard", icon: Activity, visible: () => true },
  { href: "/analytics" as Route, label: "Analytics", icon: BarChart3, visible: () => true },
  { href: "/forecast" as Route, label: "Forecast", icon: BrainCircuit, visible: (canViewForecast: boolean) => canViewForecast },
];

export function Sidebar() {
  const pathname = usePathname();
  const session = useSessionContext();
  const visibleItems = navItems.filter((item) => item.visible(session.canViewForecast));

  return (
    <aside className="rounded-3xl border border-white/10 bg-slate-900/80 p-5 shadow-glow backdrop-blur">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.25em] text-cyan-300/80">SupplyIQ</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Control Tower</h1>
        <p className="mt-3 text-sm text-slate-300">
          Multi-layer supply intelligence for forecasting, analytics, and inventory actioning.
        </p>
      </div>

      <nav className="space-y-2">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition",
                pathname === item.href
                  ? "bg-cyan-400/20 text-white"
                  : "text-slate-300 hover:bg-white/5 hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
        {session.canViewPipeline ? (
          <Link
            href={"/pipeline" as Route}
            className={clsx(
              "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition",
              pathname === "/pipeline" ? "bg-cyan-400/20 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white",
            )}
          >
            <ShieldCheck className="h-4 w-4" />
            Pipeline
          </Link>
        ) : null}
      </nav>

      <div className="mt-8 rounded-2xl border border-emerald-400/15 bg-emerald-400/10 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-emerald-100">
          <ShieldCheck className="h-4 w-4" />
          Protected workspace
        </div>
        <p className="mt-2 text-sm text-slate-300">
          Clerk middleware and backend JWT validation are ready when environment keys are enabled.
        </p>
      </div>
    </aside>
  );
}
