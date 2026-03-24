"use client";

import { SupplierPerformanceChart } from "@/components/charts/SupplierPerformanceChart";
import { DataTable } from "@/components/ui/DataTable";
import { SectionCard } from "@/components/ui/SectionCard";
import { useInventoryPositions, useSupplierPerformance } from "@/lib/hooks";

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

export default function AnalyticsPage() {
  const supplierPerformance = useSupplierPerformance();
  const inventoryPositions = useInventoryPositions();

  if (supplierPerformance.error || inventoryPositions.error) {
    return <ErrorState message="Unable to load analytics. Check backend connectivity or your session token." />;
  }

  if (!supplierPerformance.data || !inventoryPositions.data) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1.1fr_minmax(0,1fr)]">
        <SectionCard
          title="Supplier On-Time Rate"
          subtitle="Shipment-truthful on-time delivery performance by supplier."
        >
          <SupplierPerformanceChart items={supplierPerformance.data.items} />
        </SectionCard>

        <SectionCard
          title="Supplier Shipment Register"
          subtitle="Operational supplier view across delivered, delayed, and in-transit shipment counts."
        >
          <div className="space-y-3">
            {supplierPerformance.data.items.map((item) => (
              <div key={item.supplier_name} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{item.supplier_name}</p>
                    <p className="text-sm text-slate-400">{item.shipment_count} tracked shipments</p>
                  </div>
                  <span className="rounded-full bg-orange-400/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-orange-200">
                    {item.on_time_rate_pct}% on time
                  </span>
                </div>
                <div className="mt-4 grid gap-3 text-sm text-slate-300 md:grid-cols-4">
                  <p>Delivered: {item.delivered_count}</p>
                  <p>Delayed: {item.delayed_count}</p>
                  <p>In Transit: {item.in_transit_count}</p>
                  <p>On Time: {item.on_time_rate_pct}%</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Inventory Position Grid"
        subtitle="Current inventory footprint across regions, including days of cover and risk levels."
      >
        <DataTable
          rows={inventoryPositions.data.items}
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
