"use client";

import { DemandAreaChart } from "@/components/charts/DemandAreaChart";
import { DataTable } from "@/components/ui/DataTable";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";
import { useAlerts, useAnalyticsOverview, useStockouts } from "@/lib/hooks";

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

export default function DashboardPage() {
  const overview = useAnalyticsOverview();
  const alerts = useAlerts();
  const stockouts = useStockouts();

  if (overview.error || alerts.error || stockouts.error) {
    return <ErrorState message="Unable to load the dashboard. Check backend connectivity or your session token." />;
  }

  if (!overview.data || !alerts.data || !stockouts.data) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {overview.data.kpis.map((kpi) => (
          <StatCard
            key={kpi.label}
            label={kpi.label}
            value={`${kpi.value}${kpi.unit ? ` ${kpi.unit}` : ""}`}
            note={kpi.change_note}
            accent={kpi.label.includes("Risk") ? "rose" : "teal"}
          />
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_minmax(0,0.95fr)]">
        <SectionCard
          title="Demand Momentum"
          subtitle="Six-period demand shape derived from current inventory and planning coverage."
        >
          <DemandAreaChart points={overview.data.demand_series} />
        </SectionCard>

        <SectionCard
          title="Active Alerts"
          subtitle="Most recent disruption signals flowing through the supply network."
        >
          <div className="space-y-3">
            {alerts.data.items.map((alert) => (
              <div key={alert.alert_id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{alert.product_name}</p>
                    <p className="text-sm text-slate-400">{alert.region_name}</p>
                  </div>
                  <span className="rounded-full bg-rose-400/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-rose-200">
                    {alert.severity}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-300">{alert.message}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Stockout Candidates"
        subtitle="Inventory positions already below reorder threshold and likely to need intervention."
      >
        <DataTable
          rows={stockouts.data.items}
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
            { key: "reorder", header: "Reorder Point", render: (row) => row.reorder_point },
            { key: "risk", header: "Risk", render: (row) => row.risk_level },
          ]}
        />
      </SectionCard>
    </div>
  );
}
