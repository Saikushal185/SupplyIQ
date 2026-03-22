import { fetchInventoryPositions } from "@/lib/api";
import { ForecastWorkspace } from "@/components/ui/ForecastWorkspace";
import { SectionCard } from "@/components/ui/SectionCard";

export default async function ForecastPage() {
  const positions = await fetchInventoryPositions();

  return (
    <div className="space-y-6">
      <SectionCard
        title="Forecast Workbench"
        subtitle="Generate new demand forecasts, inspect latest results, and review persisted history for each product."
      >
        <ForecastWorkspace positions={positions.items} />
      </SectionCard>
    </div>
  );
}
