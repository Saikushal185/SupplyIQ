"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Activity, BarChart3, BrainCircuit, ChevronLeft, ChevronRight, ShieldCheck, X } from "lucide-react";

import { useSessionContext } from "@/context/session-context";

interface SidebarProps {
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleCollapse: () => void;
  onCloseMobile: () => void;
}

interface NavItem {
  href: Route;
  label: string;
  icon: typeof Activity;
  visible: (canViewForecast: boolean) => boolean;
}

const navItems: NavItem[] = [
  { href: "/dashboard" as Route, label: "Dashboard", icon: Activity, visible: () => true },
  { href: "/analytics" as Route, label: "Analytics", icon: BarChart3, visible: () => true },
  { href: "/forecast" as Route, label: "Forecast", icon: BrainCircuit, visible: (canViewForecast) => canViewForecast },
];

export function Sidebar({ collapsed, mobileOpen, onToggleCollapse, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const session = useSessionContext();
  const visibleItems = navItems.filter((item) => item.visible(session.canViewForecast));

  return (
    <>
      <button
        type="button"
        aria-label="Close sidebar overlay"
        className={clsx(
          "fixed inset-0 z-30 bg-slate-950/70 transition lg:hidden",
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onCloseMobile}
      />
      <aside
        className={clsx(
          "fixed inset-y-4 left-4 z-40 flex flex-col rounded-[32px] border border-white/10 bg-app-surface/95 px-4 py-5 shadow-panel backdrop-blur transition-transform duration-200 lg:sticky lg:left-0 lg:top-4 lg:h-[calc(100vh-2rem)]",
          collapsed ? "w-[92px] lg:w-[96px]" : "w-[292px] lg:w-[292px]",
          mobileOpen ? "translate-x-0" : "-translate-x-[120%] lg:translate-x-0",
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className={clsx("min-w-0", collapsed && "lg:flex lg:w-full lg:justify-center")}>
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 text-lg font-semibold text-white shadow-glow">
                SI
              </div>
              <div className={clsx(collapsed && "lg:hidden")}>
                <p className="eyebrow">SupplyIQ</p>
                <h1 className="mt-2 text-xl font-semibold text-white">Control Tower</h1>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 hover:text-white lg:hidden"
              onClick={onCloseMobile}
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </button>
            <button
              type="button"
              className="hidden h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 hover:text-white lg:inline-flex"
              onClick={onToggleCollapse}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <div className={clsx("mt-6 rounded-[24px] border border-white/10 bg-slate-950/45 p-4", collapsed && "lg:hidden")}>
          <p className="text-sm text-slate-300">
            Inventory, forecasting, and supplier risk in a single operational workspace.
          </p>
        </div>

        <nav className="mt-6 flex-1 space-y-2">
          {visibleItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm font-medium transition",
                  active
                    ? "border-indigo-400/30 bg-indigo-400/15 text-white"
                    : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/5 hover:text-white",
                  collapsed && "lg:justify-center",
                )}
                onClick={onCloseMobile}
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span className={clsx(collapsed && "lg:hidden")}>{item.label}</span>
              </Link>
            );
          })}

          {session.canViewPipeline ? (
            <Link
              href={"/pipeline" as Route}
              className={clsx(
                "flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm font-medium transition",
                pathname === "/pipeline"
                  ? "border-cyan-400/30 bg-cyan-400/15 text-white"
                  : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/5 hover:text-white",
                collapsed && "lg:justify-center",
              )}
              onClick={onCloseMobile}
            >
              <ShieldCheck className="h-5 w-5 shrink-0" />
              <span className={clsx(collapsed && "lg:hidden")}>Pipeline</span>
            </Link>
          ) : null}
        </nav>

        <div className={clsx("rounded-[24px] border border-cyan-400/15 bg-cyan-400/10 p-4", collapsed && "lg:px-2 lg:text-center")}>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">Secure Workspace</p>
          <p className={clsx("mt-2 text-sm text-slate-300", collapsed && "lg:hidden")}>
            Clerk-backed access and role-aware forecast permissions are active throughout the shell.
          </p>
        </div>
      </aside>
    </>
  );
}
