"use client";

import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Activity, BarChart3, BrainCircuit, Radar, ShieldCheck } from "lucide-react";

import type { UserRole } from "@/types";

interface NavItem {
  href: string;
  label: string;
  icon: typeof Activity;
  roles: UserRole[];
}

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: Activity, roles: ["admin", "analyst", "viewer"] },
  { href: "/analytics", label: "Analytics", icon: BarChart3, roles: ["admin", "analyst", "viewer"] },
  { href: "/forecast", label: "Forecast", icon: BrainCircuit, roles: ["admin", "analyst"] },
  { href: "/pipeline", label: "Pipeline", icon: Radar, roles: ["admin"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const role = (typeof user?.publicMetadata?.role === "string" ? user.publicMetadata.role : "viewer") as UserRole;
  const allowedNavItems = navItems.filter((item) => item.roles.includes(role));

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
        {allowedNavItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href as never}
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
      </nav>

      <div className="mt-8 rounded-2xl border border-emerald-400/15 bg-emerald-400/10 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-emerald-100">
          <ShieldCheck className="h-4 w-4" />
          Protected workspace
        </div>
        <p className="mt-2 text-sm text-slate-300">
          Clerk sessions drive route access, role-aware navigation, and backend JWT authorization.
        </p>
      </div>
    </aside>
  );
}
