"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { AlertTriangle, CalendarClock, DatabaseZap } from "lucide-react";

import { EChart } from "@/components/charts/EChart";
import { DataTable } from "@/components/ui/DataTable";
import { SectionCard } from "@/components/ui/SectionCard";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useSessionContext } from "@/context/session-context";
import {
  buildSalesTrend,
  buildTopProducts,
  formatDateTime,
  getMonthStartIsoDate,
  getRelativeDateRange,
  getTodayIsoDate,
  pipelineStatusVariant,
  severityToVariant,
} from "@/lib/insights";
import {
  useForecastRunCount,
  useInventorySummary,
  useLowStock,
  usePipelineStatus,
  useProductSales,
  useSalesAnalytics,
} from "@/lib/hooks";
import { isDashboardReady } from "@/lib/view-state";

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="panel-surface p-5">
            <SkeletonBlock className="h-4 w-28" />
            <SkeletonBlock className="mt-4 h-10 w-32" />
            <SkeletonBlock className="mt-6 h-4 w-full" />
          </div>
        ))}
      </section>
      <section className="grid gap-6 xl:grid-cols-2">
        {Array.from({ length: 2 }).map((_, index) => (
          <div key={index} className="panel-surface p-6">
            <SkeletonBlock className="h-4 w-32" />
            <SkeletonBlock className="mt-3 h-4 w-64" />
            <SkeletonBlock className="mt-6 h-[320px] w-full rounded-[24px]" />
          </div>
        ))}
      </section>
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <div className="panel-surface p-6">
          <SkeletonBlock className="h-4 w-40" />
          <SkeletonBlock className="mt-3 h-4 w-72" />
          <SkeletonBlock className="mt-6 h-[340px] w-full rounded-[24px]" />
        </div>
        <div className="panel-surface p-6">
          <SkeletonBlock className="h-4 w-32" />
          <SkeletonBlock className="mt-3 h-4 w-52" />
          <div className="mt-6 space-y-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <SkeletonBlock key={index} className="h-20 w-full rounded-[24px]" />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="panel-surface flex items-start gap-4 p-6 text-rose-100">
      <AlertTriangle className="mt-1 h-5 w-5 shrink-0" />
      <div>
        <p className="text-lg font-semibold text-white">Dashboard data is unavailable</p>
        <p className="mt-2 text-sm text-rose-100/90">{message}</p>
      </div>
    </div>
  );
}

export function DashboardPageClient() {
  const session = useSessionContext();
  const trendRange = useMemo(() => getRelativeDateRange(30), []);
  const monthStart = useMemo(() => getMonthStartIsoDate(), []);
  const today = useMemo(() => getTodayIsoDate(), []);

  const inventorySummary = useInventorySummary();
  const lowStock = useLowStock();
  const sales = useSalesAnalytics(trendRange.startDate, trendRange.endDate);
  const productSales = useProductSales(monthStart, today);
  const forecastRunCount = useForecastRunCount(today);
  const pipelineStatus = usePipelineStatus(session.canViewPipeline);
  const inventorySummaryData = inventorySummary.data;
  const lowStockData = lowStock.data;
  const salesData = sales.data;
  const productSalesData = productSales.data;
  const forecastRunCountData = forecastRunCount.data;
  const pipelineStatusData = pipelineStatus.data;

  const requiredErrors = [inventorySummary.error, lowStock.error, sales.error, productSales.error, forecastRunCount.error].filter(Boolean);
  if (requiredErrors.length) {
    return <ErrorState message="Check the backend API connection and active session token, then refresh the dashboard." />;
  }

  const requiredReady = isDashboardReady({
    hasInventorySummary: Boolean(inventorySummaryData),
    hasLowStock: Boolean(lowStockData),
    hasSales: Boolean(salesData),
    hasProductSales: Boolean(productSalesData),
    hasForecastRunCount: Boolean(forecastRunCountData),
    canViewPipeline: session.canViewPipeline,
    hasPipelineStatus: Boolean(pipelineStatusData),
    hasPipelineStatusError: Boolean(pipelineStatus.error),
  });

  if (!requiredReady) {
    return <DashboardSkeleton />;
  }

  const summaryRows = inventorySummaryData!.data;
  const lowStockRows = lowStockData!.data;
  const salesRows = salesData!.data;
  const productSalesRows = productSalesData!.data;
  const salesTrend = buildSalesTrend(salesRows);
  const topProducts = buildTopProducts(productSalesRows);

  const totalSkusInStock = new Set(summaryRows.filter((row) => row.quantity > 0).map((row) => row.sku)).size;
  const regionsActive = new Set(summaryRows.map((row) => row.region_id)).size;
  const forecastsRunToday = forecastRunCountData!.data.count;

  const salesTrendOption: EChartsOption = {
    backgroundColor: "transparent",
    color: ["#6366f1", "#06b6d4"],
    tooltip: { trigger: "axis" },
    grid: { top: 24, right: 16, bottom: 24, left: 16, containLabel: true },
    xAxis: {
      type: "category",
      data: salesTrend.labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.22)" } },
      axisLabel: { color: "#94a3b8" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        data: salesTrend.values,
        showSymbol: false,
        lineStyle: { width: 3, color: "#6366f1" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(99,102,241,0.35)" },
              { offset: 1, color: "rgba(99,102,241,0.02)" },
            ],
          },
        },
      },
    ],
  };

  const topProductsOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { top: 24, right: 16, bottom: 36, left: 16, containLabel: true },
    xAxis: {
      type: "category",
      data: topProducts.map((product) => product.label),
      axisLabel: {
        color: "#94a3b8",
        interval: 0,
        rotate: 18,
      },
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.22)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    series: [
      {
        type: "bar",
        data: topProducts.map((product) => product.value),
        itemStyle: {
          borderRadius: [12, 12, 0, 0],
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "#06b6d4" },
              { offset: 1, color: "#6366f1" },
            ],
          },
        },
      },
    ],
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total SKUs in stock"
          value={totalSkusInStock.toLocaleString()}
          note="Distinct active SKUs with on-hand inventory across the network."
          accent="indigo"
        />
        <StatCard
          label="Regions active"
          value={regionsActive.toLocaleString()}
          note="Operating regions currently represented in the latest inventory snapshot."
          accent="cyan"
        />
        <StatCard
          label="Low stock alerts"
          value={lowStockRows.length.toLocaleString()}
          note="Positions below reorder point and ready for replenishment action."
          accent="amber"
        />
        <StatCard
          label="Forecasts run today"
          value={forecastsRunToday.toLocaleString()}
          note="Seven-day forecast jobs generated across products and regions today."
          accent="emerald"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          title="30-Day Total Sales Trend"
          subtitle="Daily units sold across all regions combined over the last thirty days."
        >
          <EChart option={salesTrendOption} height={320} />
        </SectionCard>

        <SectionCard
          title="Top 5 Products By Units Sold"
          subtitle="Current-month leaders ranked by units sold across all active regions."
        >
          <EChart option={topProductsOption} height={320} />
        </SectionCard>
      </section>

      <section className={`grid gap-6 ${session.canViewPipeline ? "xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]" : "grid-cols-1"}`}>
        <SectionCard
          title="Low Stock Products"
          subtitle="Priority replenishment watchlist with current quantity, reorder points, and risk status."
        >
          <DataTable
            rows={lowStockRows}
            rowKey={(row) => `${row.product_id}:${row.region_id}`}
            emptyMessage="No low-stock products right now."
            columns={[
              {
                key: "sku",
                header: "SKU",
                render: (row) => <span className="mono-data text-slate-100">{row.sku}</span>,
              },
              {
                key: "name",
                header: "Name",
                render: (row) => (
                  <div>
                    <p className="font-medium text-white">{row.product_name}</p>
                    <p className="text-xs text-slate-500">{row.region_name}</p>
                  </div>
                ),
              },
              {
                key: "region",
                header: "Region",
                render: (row) => row.region_name,
              },
              {
                key: "qty",
                header: "Current Qty",
                render: (row) => <span className="mono-data">{row.quantity.toLocaleString()}</span>,
              },
              {
                key: "reorder",
                header: "Reorder Point",
                render: (row) => <span className="mono-data">{row.reorder_point?.toLocaleString() ?? "-"}</span>,
              },
              {
                key: "status",
                header: "Status",
                render: (row) => (
                  <StatusBadge label={row.risk_level} variant={severityToVariant(row.risk_level)} />
                ),
              },
            ]}
          />
        </SectionCard>

        {session.canViewPipeline ? (
          <SectionCard
            title="Pipeline Status"
            subtitle="Latest operational run health, refresh cadence, and next scheduled execution."
          >
            {pipelineStatus.error ? (
              <div className="rounded-[24px] border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-100">
                Unable to load pipeline status right now.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm text-slate-400">Status</p>
                      <p className="mt-2 text-xl font-semibold text-white">{pipelineStatusData?.data.state_name ?? "Unavailable"}</p>
                    </div>
                    <StatusBadge
                      label={pipelineStatusData?.data.state_name ?? "Unknown"}
                      variant={pipelineStatusVariant(pipelineStatusData?.data)}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
                  <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <CalendarClock className="h-4 w-4" />
                      Last run time
                    </div>
                    <p className="mono-data mt-3 text-lg text-white">{formatDateTime(pipelineStatusData?.data.start_time)}</p>
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <DatabaseZap className="h-4 w-4" />
                      Next scheduled run
                    </div>
                    <p className="mono-data mt-3 text-lg text-white">
                      {formatDateTime(pipelineStatusData?.data.next_scheduled_run_time)}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </SectionCard>
        ) : null}
      </section>
    </div>
  );
}
