import { DashboardPageClient } from "@/components/pages/DashboardPageClient";
import { requireServerRole } from "@/lib/auth";

export default async function DashboardPage() {
  await requireServerRole(["admin", "analyst", "viewer"]);
  return <DashboardPageClient />;
}
