"use client";

import Link from "next/link";
import { BellRing, Menu, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { usePathname } from "next/navigation";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { useSessionContext } from "@/context/session-context";

interface TopbarProps {
  isSidebarCollapsed: boolean;
  onToggleDesktopSidebar: () => void;
  onToggleMobileSidebar: () => void;
}

const pageTitles: Record<string, string> = {
  "/dashboard": "Network Dashboard",
  "/analytics": "Analytics Command Center",
  "/forecast": "Forecast Studio",
  "/pipeline": "Pipeline Monitor",
  "/login": "Secure Sign In",
};

function getInitials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "SI";
}

export function Topbar({ isSidebarCollapsed, onToggleDesktopSidebar, onToggleMobileSidebar }: TopbarProps) {
  const pathname = usePathname();
  const session = useSessionContext();
  const title = pageTitles[pathname] ?? "SupplyIQ";
  const initials = getInitials(session.displayName);

  return (
    <header className="panel-surface flex flex-wrap items-center justify-between gap-4 px-5 py-4 md:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 hover:text-white lg:hidden"
          onClick={onToggleMobileSidebar}
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <button
          type="button"
          className="hidden h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 hover:text-white lg:inline-flex"
          onClick={onToggleDesktopSidebar}
          aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        </button>
        <div>
          <p className="eyebrow">Operational View</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white md:text-[2rem]">{title}</h2>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-100 md:flex">
          <BellRing className="h-4 w-4" />
          Real-time supply intelligence
        </div>

        <div className="flex items-center gap-3 rounded-[24px] border border-white/10 bg-slate-950/55 px-3 py-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 text-sm font-semibold text-white shadow-glow">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">{session.displayName}</p>
            <p className="truncate text-xs text-slate-400">{session.primaryEmail ?? "No verified email"}</p>
          </div>
          <StatusBadge label={session.roleLabel} variant="indigo" className="hidden sm:inline-flex" />
        </div>

        {!session.isSignedIn ? (
          <Link
            href="/login"
            className="inline-flex items-center rounded-full border border-indigo-400/25 bg-indigo-400/10 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-400/15"
          >
            Sign in
          </Link>
        ) : null}
      </div>
    </header>
  );
}
