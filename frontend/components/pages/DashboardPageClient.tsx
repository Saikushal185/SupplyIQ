"use client";

import { DemandAreaChart } from "@/components/charts/DemandAreaChart";
import { DataTable } from "@/components/ui/DataTable";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";
import { useInventorySummary, useLowStock, useSalesAnalytics } from "@/lib/hooks";
import type { DemandPoint } from "@/types";

function LoadingState() {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 text-sm text-slate-300">
      Loading live dashboard data...
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 p-6 text-sm text-rose-100">{message}</div>
  );
}

function buildDemandSeries(
  salesRows: {
    sale_date: string;
    units_sold: number;
  }[],
): DemandPoint[] {
  const totalsByDate = new Map<string, number>();
  salesRows.forEach((row) => {
    totalsByDate.set(row.sale_date, (totalsByDate.get(row.sale_date) ?? 0) + row.units_sold);
  });

  return [...totalsByDate.entries()].slice(-6).map(([saleDate, unitsSold]) => ({
    label: new Date(saleDate).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    demand_units: unitsSold,
  }));
}

export function DashboardPageClient() {
  const inventorySummary = useInventorySummary();
  const lowStock = useLowStock();
  const sales = useSalesAnalytics();

  if (inventorySummary.error || lowStock.error || sales.error) {
    return <ErrorState message="Unable to load the dashboard. Check backend connectivity or your session token." />;
  }

  if (!inventorySummary.data || !lowStock.data || !sales.data) {
    return <LoadingState />;
  }

  const summaryRows = inventorySummary.data.data;
  const lowStockRows = lowStock.data.data;
  const salesRows = sales.data.data;
  const totalInventoryUnits = summaryRows.reduce((sum, row) => sum + row.quantity, 0);
  const totalRevenue = salesRows.reduce((sum, row) => sum + row.revenue, 0);
  const demandSeries = buildDemandSeries(salesRows);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Inventory Units" value={totalInventoryUnits.toLocaleString()} note="Latest stock across all product-region positions." accent="teal" />
        <StatCard label="Tracked Positions" value={summaryRows.length.toLocaleString()} note="Live product-region combinations currently represented in inventory." accent="teal" />
        <StatCard label="Low-Stock Positions" value={lowStockRows.length.toLocaleString()} note="Positions currently below reorder point and needing attention." accent="rose" />
        <StatCard
          label="Recent Revenue"
          value={`$${totalRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          note="Revenue captured in the current sales analytics window."
          accent="teal"
        />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_minmax(0,0.95fr)]">
        <SectionCard
          title="Demand Momentum"
          subtitle="Recent daily units sold rolled up across regions from the sales analytics feed."
        >
          <DemandAreaChart points={demandSeries} />
        </SectionCard>

        <SectionCard
          title="Low-Stock Watchlist"
          subtitle="Highest-priority product-region positions that are already below reorder point."
        >
          <div className="space-y-3">
            {lowStockRows.slice(0, 5).map((row) => (
              <div key={`${row.product_id}-${row.region_id}`} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{row.product_name}</p>
                    <p className="text-sm text-slate-400">{row.region_name}</p>
                  </div>
                  <span className="rounded-full bg-rose-400/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-rose-200">
                    {row.risk_level}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-300">
                  {row.quantity} units on hand against a reorder point of {row.reorder_point ?? "n/a"}.
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Inventory Summary"
        subtitle="Current stock levels across every tracked product and region."
      >
        <DataTable
          rows={summaryRows}
          columns={[
            {
              key: "product",
              header: "Product",
              render: (row) => (
                <div>
                  <p className="font-medium text-white">{row.product_name}</p>
                  <p className="text-xs text-slate-400">{row.sku}</p>
                </div>
              ),
            },
            { key: "region", header: "Region", render: (row) => row.region_name },
            { key: "quantity", header: "Quantity", render: (row) => row.quantity },
            { key: "snapshot", header: "Snapshot", render: (row) => row.snapshot_date },
            { key: "reorder", header: "Reorder Point", render: (row) => row.reorder_point ?? "n/a" },
            { key: "risk", header: "Risk", render: (row) => row.risk_level },
          ]}
        />
      </SectionCard>
    </div>
  );
}
