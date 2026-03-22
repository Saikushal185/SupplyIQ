"use client";

import { usePathname } from "next/navigation";

const pageTitles: Record<string, string> = {
  "/dashboard": "Network Dashboard",
  "/analytics": "Analytics Studio",
  "/forecast": "Forecast Workbench",
  "/login": "Authentication",
};

export function Topbar() {
  const pathname = usePathname();
  const title = pageTitles[pathname] ?? "SupplyIQ";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-white/10 bg-slate-900/60 px-5 py-4 backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Operational View</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">{title}</h2>
      </div>
      <div className="rounded-full border border-teal-400/20 bg-teal-400/10 px-4 py-2 text-sm text-teal-200">
        AI-powered supply chain intelligence
      </div>
    </header>
  );
}
