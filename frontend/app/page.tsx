import { redirect } from "next/navigation";

import { getServerSessionSnapshot } from "@/lib/auth";
import { getDefaultRouteForRole } from "@/lib/roles";

export default async function HomePage() {
  const session = await getServerSessionSnapshot();
  if (!session.isSignedIn) {
    redirect("/login");
  }

  redirect(getDefaultRouteForRole(session.role));
}
