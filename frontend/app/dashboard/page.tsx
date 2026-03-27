import { redirect } from "next/navigation";

import { DashboardPageClient } from "@/components/pages/DashboardPageClient";
import { getServerSessionSnapshot } from "@/lib/auth";
import { isClerkConfigured } from "@/lib/auth-config";

export default async function DashboardPage() {
  const session = await getServerSessionSnapshot();

  if (isClerkConfigured() && !session.isSignedIn) {
    redirect("/login");
  }

  return <DashboardPageClient />;
}
