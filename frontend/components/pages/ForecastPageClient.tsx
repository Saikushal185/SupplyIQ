"use client";

import { ForecastWorkspace } from "@/components/ui/ForecastWorkspace";
import { SectionCard } from "@/components/ui/SectionCard";
import { useInventorySummary } from "@/lib/hooks";

function LoadingState() {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 text-sm text-slate-300">
      Loading forecast scopes...
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 p-6 text-sm text-rose-100">{message}</div>
  );
}

export function ForecastPageClient() {
  const positions = useInventorySummary();

  if (positions.error) {
    return <ErrorState message="Unable to load forecast scopes. Check backend connectivity or your session token." />;
  }

  if (!positions.data) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <SectionCard
        title="Forecast Workbench"
        subtitle="Generate new demand forecasts, inspect the latest saved run, and review product history."
      >
        <ForecastWorkspace positions={positions.data.data} />
      </SectionCard>
    </div>
  );
}
