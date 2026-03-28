"use client";

import type { PropsWithChildren } from "react";
import { useState } from "react";
import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const isAuthRoute = pathname.startsWith("/login");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  if (isAuthRoute) {
    return <div className="min-h-screen">{children}</div>;
  }

  return (
    <div className="min-h-screen">
      <div className="flex min-h-screen">
        <Sidebar
          collapsed={isSidebarCollapsed}
          mobileOpen={isMobileSidebarOpen}
          onCloseMobile={() => setIsMobileSidebarOpen(false)}
          onToggleCollapse={() => setIsSidebarCollapsed((value) => !value)}
        />
        <div className="flex min-h-screen min-w-0 flex-1 flex-col px-4 py-4 lg:px-6 lg:py-6">
          <Topbar
            isSidebarCollapsed={isSidebarCollapsed}
            onToggleDesktopSidebar={() => setIsSidebarCollapsed((value) => !value)}
            onToggleMobileSidebar={() => setIsMobileSidebarOpen((value) => !value)}
          />
          <main className="mt-6 flex-1">{children}</main>
        </div>
      </div>
    </div>
  );
}
