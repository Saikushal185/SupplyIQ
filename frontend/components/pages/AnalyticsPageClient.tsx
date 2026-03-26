"use client";

import { SupplierPerformanceChart } from "@/components/charts/SupplierPerformanceChart";
import { DataTable } from "@/components/ui/DataTable";
import { SectionCard } from "@/components/ui/SectionCard";
import { useInventoryTurnover, useRegionalGrowth, useSalesAnalytics, useSupplierReliability } from "@/lib/hooks";

function LoadingState() {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 text-sm text-slate-300">
      Loading supplier and inventory analytics...
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 p-6 text-sm text-rose-100">{message}</div>
  );
}

export function AnalyticsPageClient() {
  const supplierReliability = useSupplierReliability();
  const inventoryTurnover = useInventoryTurnover();
  const regionalGrowth = useRegionalGrowth();
  const salesAnalytics = useSalesAnalytics();

  if (supplierReliability.error || inventoryTurnover.error || regionalGrowth.error || salesAnalytics.error) {
    return <ErrorState message="Unable to load analytics. Check backend connectivity or your session token." />;
  }

  if (!supplierReliability.data || !inventoryTurnover.data || !regionalGrowth.data || !salesAnalytics.data) {
    return <LoadingState />;
  }

  const supplierRows = supplierReliability.data.data;
  const turnoverRows = inventoryTurnover.data.data;
  const growthRows = regionalGrowth.data.data;
  const salesRows = salesAnalytics.data.data;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1.1fr_minmax(0,1fr)]">
        <SectionCard
          title="Supplier Reliability"
          subtitle="On-time delivery performance aggregated from supplier shipment history."
        >
          <SupplierPerformanceChart items={supplierRows} />
        </SectionCard>

        <SectionCard
          title="Regional Growth"
          subtitle="Latest month-over-month revenue growth across each operating region."
        >
          <div className="space-y-3">
            {growthRows.map((item) => (
              <div key={item.region_id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{item.region_name}</p>
                    <p className="text-sm text-slate-400">
                      {new Date(item.current_month).toLocaleDateString(undefined, { month: "long", year: "numeric" })}
                    </p>
                  </div>
                  <span className="rounded-full bg-teal-400/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-teal-100">
                    {item.growth_pct}%
                  </span>
                </div>
                <div className="mt-4 grid gap-3 text-sm text-slate-300 md:grid-cols-3">
                  <p>Revenue: ${item.revenue.toLocaleString()}</p>
                  <p>Previous: ${item.previous_revenue.toLocaleString()}</p>
                  <p>Growth: {item.growth_pct}%</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Inventory Turnover"
        subtitle="Cost of goods sold divided by average inventory value for the active analytics window."
      >
        <DataTable
          rows={turnoverRows}
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
            { key: "cogs", header: "COGS", render: (row) => `$${row.cost_of_goods.toLocaleString()}` },
            { key: "avg", header: "Avg Inventory", render: (row) => `$${row.average_inventory_value.toLocaleString()}` },
            { key: "turnover", header: "Turnover Ratio", render: (row) => row.turnover_ratio.toFixed(2) },
          ]}
        />
      </SectionCard>

      <SectionCard
        title="Sales Register"
        subtitle="Daily sales aggregated by region for the default analytics date window."
      >
        <DataTable
          rows={salesRows}
          columns={[
            { key: "date", header: "Date", render: (row) => row.sale_date },
            { key: "region", header: "Region", render: (row) => row.region_name },
            { key: "units", header: "Units Sold", render: (row) => row.units_sold },
            { key: "revenue", header: "Revenue", render: (row) => `$${row.revenue.toLocaleString()}` },
          ]}
        />
      </SectionCard>
    </div>
  );
}
