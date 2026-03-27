"use client";

import Link from "next/link";
import { BellRing, LockKeyhole, LogIn, UserCircle2 } from "lucide-react";
import { usePathname } from "next/navigation";

import { useSessionContext } from "@/context/session-context";

const pageTitles: Record<string, string> = {
  "/dashboard": "Network Dashboard",
  "/analytics": "Analytics Studio",
  "/forecast": "Forecast Workbench",
  "/login": "Authentication",
};

export function Topbar() {
  const pathname = usePathname();
  const session = useSessionContext();
  const title = pageTitles[pathname] ?? "SupplyIQ";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-white/10 bg-slate-900/60 px-5 py-4 backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Operational View</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">{title}</h2>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-100">
          <BellRing className="h-4 w-4" />
          AI-powered supply chain intelligence
        </div>

        <div className="flex items-center gap-3 rounded-full border border-white/10 bg-slate-950/70 px-4 py-2 text-sm text-slate-200">
          <UserCircle2 className="h-4 w-4 text-slate-400" />
          <div className="leading-tight">
            <p>{session.displayName}</p>
            <p className="text-xs text-slate-400">{session.primaryEmail ?? session.roleLabel}</p>
          </div>
          <LockKeyhole className="h-4 w-4 text-emerald-300" />
        </div>

        {!session.isSignedIn ? (
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-100 transition hover:bg-emerald-400/15"
          >
            <LogIn className="h-4 w-4" />
            Sign in
          </Link>
        ) : null}
      </div>
    </header>
  );
}
