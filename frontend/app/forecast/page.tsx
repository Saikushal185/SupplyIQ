import { redirect } from "next/navigation";

import { ForecastPageClient } from "@/components/pages/ForecastPageClient";
import { getServerSessionSnapshot } from "@/lib/auth";
import { isClerkConfigured } from "@/lib/auth-config";
import { getDefaultRouteForRole } from "@/lib/roles";

export default async function ForecastPage() {
  const session = await getServerSessionSnapshot();

  if (isClerkConfigured() && !session.isSignedIn) {
    redirect("/login");
  }

  if (!session.canViewForecast) {
    redirect(getDefaultRouteForRole(session.role));
  }

  return <ForecastPageClient />;
}
