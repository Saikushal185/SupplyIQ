import { redirect } from "next/navigation";

import { AnalyticsPageClient } from "@/components/pages/AnalyticsPageClient";
import { getServerSessionSnapshot } from "@/lib/auth";
import { isClerkConfigured } from "@/lib/auth-config";

export default async function AnalyticsPage() {
  const session = await getServerSessionSnapshot();

  if (isClerkConfigured() && !session.isSignedIn) {
    redirect("/login");
  }

  return <AnalyticsPageClient />;
}
