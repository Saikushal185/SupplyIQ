"use client";

import type { PropsWithChildren } from "react";
import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const isAuthRoute = pathname === "/login";

  if (isAuthRoute) {
    return <div className="page-stack">{children}</div>;
  }

  return (
    <div className="data-grid p-4 lg:p-6">
      <Sidebar />
      <main className="page-stack gap-6">
        <Topbar />
        {children}
      </main>
    </div>
  );
}
