"use client";

import { ForecastWorkspace } from "@/components/ui/ForecastWorkspace";
import { SectionCard } from "@/components/ui/SectionCard";
import { useInventoryPositions } from "@/lib/hooks";

export default function ForecastPage() {
  const positions = useInventoryPositions();

  if (positions.error) {
    return (
      <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 p-6 text-sm text-rose-100">
        Unable to load forecast scopes. Check backend connectivity or your session token.
      </div>
    );
  }

  if (!positions.data) {
    return (
      <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 text-sm text-slate-300">
        Loading forecast scopes...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionCard
        title="Forecast Workbench"
        subtitle="Generate new demand forecasts, inspect latest results, and review persisted history for each product."
      >
        <ForecastWorkspace positions={positions.data.items} />
      </SectionCard>
    </div>
  );
}
