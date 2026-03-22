import { fetchAlerts, fetchAnalyticsOverview, fetchStockouts } from "@/lib/api";
import { DemandAreaChart } from "@/components/charts/DemandAreaChart";
import { DataTable } from "@/components/ui/DataTable";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatCard } from "@/components/ui/StatCard";

export default async function DashboardPage() {
  const [overview, alerts, stockouts] = await Promise.all([
    fetchAnalyticsOverview(),
    fetchAlerts(),
    fetchStockouts(),
  ]);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {overview.kpis.map((kpi) => (
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
          <DemandAreaChart points={overview.demand_series} />
        </SectionCard>

        <SectionCard
          title="Active Alerts"
          subtitle="Most recent disruption signals flowing through the supply network."
        >
          <div className="space-y-3">
            {alerts.items.map((alert) => (
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
          rows={stockouts.items}
          columns={[
            { key: "product", header: "Product", render: (row) => <div><p className="font-medium text-white">{row.product_name}</p><p className="text-xs text-slate-400">{row.sku}</p></div> },
            { key: "region", header: "Region", render: (row) => row.region_name },
            { key: "onhand", header: "On Hand", render: (row) => row.quantity_on_hand },
            { key: "inbound", header: "Inbound", render: (row) => row.inbound_units },
            { key: "cover", header: "Days Cover", render: (row) => row.days_of_cover },
            { key: "risk", header: "Risk", render: (row) => row.risk_level },
          ]}
        />
      </SectionCard>
    </div>
  );
}
