import { redirect } from "next/navigation";

import { PipelinePageClient } from "@/components/pages/PipelinePageClient";
import { getServerSessionSnapshot } from "@/lib/auth";
import { isClerkConfigured } from "@/lib/auth-config";
import { getDefaultRouteForRole } from "@/lib/roles";

export default async function PipelinePage() {
  const session = await getServerSessionSnapshot();

  if (isClerkConfigured() && !session.isSignedIn) {
    redirect("/login");
  }

  if (!session.canViewPipeline) {
    redirect(getDefaultRouteForRole(session.role));
  }

  return <PipelinePageClient />;
}
