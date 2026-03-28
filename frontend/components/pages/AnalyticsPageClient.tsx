"use client";

import { useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { AlertTriangle, Check, ChevronsUpDown } from "lucide-react";

import { EChart } from "@/components/charts/EChart";
import { SectionCard } from "@/components/ui/SectionCard";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  buildMonthlyPeriods,
  buildHeatmap,
  buildRevenueGrowthSeries,
  buildSupplierReliabilitySeries,
  buildTurnoverTrendSeries,
  formatCurrency,
  getRelativeDateRange,
  reliabilityColor,
  weekdayLabels,
} from "@/lib/insights";
import {
  useAnalyticsFilters,
  useInventoryTurnoverTrend,
  useSalesAnalytics,
  useSupplierReliability,
} from "@/lib/hooks";

function AnalyticsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="panel-surface p-5">
        <div className="grid gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonBlock key={index} className="h-12 w-full rounded-2xl" />
          ))}
        </div>
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="panel-surface p-6">
            <SkeletonBlock className="h-4 w-40" />
            <SkeletonBlock className="mt-3 h-4 w-72" />
            <SkeletonBlock className="mt-6 h-[320px] w-full rounded-[24px]" />
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="panel-surface flex items-start gap-4 p-6 text-rose-100">
      <AlertTriangle className="mt-1 h-5 w-5 shrink-0" />
      <div>
        <p className="text-lg font-semibold text-white">Analytics are unavailable</p>
        <p className="mt-2 text-sm text-rose-100/90">{message}</p>
      </div>
    </div>
  );
}

function NoDataState({ message }: { message: string }) {
  return (
    <div className="flex h-[320px] items-center justify-center rounded-[24px] border border-dashed border-white/10 bg-slate-950/35 px-6 text-center text-sm text-slate-400">
      {message}
    </div>
  );
}

export function AnalyticsPageClient() {
  const defaultRange = useMemo(() => getRelativeDateRange(180), []);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(defaultRange.startDate);
  const [endDate, setEndDate] = useState(defaultRange.endDate);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const filters = useAnalyticsFilters();
  const sales = useSalesAnalytics(startDate, endDate);
  const supplierReliability = useSupplierReliability(selectedRegions.length === 1 ? selectedRegions[0] : undefined);
  const turnoverPeriods = useMemo(() => buildMonthlyPeriods(endDate), [endDate]);
  const turnoverTrend = useInventoryTurnoverTrend(turnoverPeriods);
  const filtersData = filters.data;
  const salesData = sales.data;
  const supplierReliabilityData = supplierReliability.data;
  const turnoverTrendData = turnoverTrend.data;

  const hasError = filters.error || sales.error || supplierReliability.error || turnoverTrend.error;
  if (hasError) {
    return <ErrorState message="The analytics API did not return the expected datasets for this view." />;
  }

  if (!filtersData || !salesData || !supplierReliabilityData || !turnoverTrendData) {
    return <AnalyticsSkeleton />;
  }

  const filterOptions = filtersData.data;
  const salesRows = salesData.data;
  const heatmap = buildHeatmap(salesRows, selectedRegions);
  const supplierRows = buildSupplierReliabilitySeries(supplierReliabilityData.data);
  const revenueGrowth = buildRevenueGrowthSeries(salesRows, selectedRegions);
  const selectedCategoryProductIds =
    selectedCategory === "all"
      ? null
      : new Set(
          filterOptions.products
            .filter((product) => (product.category ?? "Uncategorized") === selectedCategory)
            .map((product) => product.product_id),
        );
  const turnoverSeries = buildTurnoverTrendSeries(turnoverTrendData.data, selectedCategoryProductIds);

  const heatmapOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: { position: "top" },
    grid: { top: 12, right: 24, bottom: 24, left: 84 },
    xAxis: {
      type: "category",
      data: weekdayLabels,
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.18)" } },
      axisLabel: { color: "#94a3b8" },
    },
    yAxis: {
      type: "category",
      data: heatmap.regions,
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.18)" } },
      axisLabel: { color: "#cbd5e1" },
    },
    visualMap: {
      min: 0,
      max: Math.max(...heatmap.values.map((entry) => entry[2]), 10),
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      textStyle: { color: "#94a3b8" },
      inRange: {
        color: ["#0f172a", "#06b6d4", "#6366f1"],
      },
    },
    series: [
      {
        type: "heatmap",
        data: heatmap.values,
        label: { show: false },
        emphasis: { itemStyle: { borderColor: "rgba(255,255,255,0.18)", borderWidth: 1 } },
      },
    ],
  };

  const turnoverOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      top: 0,
      textStyle: { color: "#cbd5e1" },
      type: "scroll",
    },
    grid: { top: 48, right: 18, bottom: 24, left: 20, containLabel: true },
    xAxis: {
      type: "category",
      data: turnoverSeries.labels,
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.18)" } },
      axisLabel: { color: "#94a3b8" },
    },
    yAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.18)" } },
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    series: turnoverSeries.series.map((series, index) => ({
      name: series.name,
      type: "line",
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 3 },
      emphasis: { focus: "series" },
      color: ["#6366f1", "#06b6d4", "#8b5cf6", "#14b8a6", "#f59e0b"][index % 5],
      data: series.data,
    })),
  };

  const supplierOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { top: 12, right: 18, bottom: 24, left: 120 },
    xAxis: {
      type: "value",
      max: 100,
      axisLabel: { color: "#94a3b8", formatter: (value: number) => `${value}%` },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    yAxis: {
      type: "category",
      data: supplierRows.map((row) => row.supplier_name),
      axisLabel: { color: "#cbd5e1" },
    },
    series: [
      {
        type: "bar",
        data: supplierRows.map((row) => ({
          value: row.on_time_rate_pct,
          itemStyle: {
            color: reliabilityColor(row.on_time_rate_pct),
            borderRadius: [0, 12, 12, 0],
          },
        })),
      },
    ],
  };

  const revenueGrowthOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) => formatCurrency(Number(value ?? 0)),
    },
    legend: {
      top: 0,
      textStyle: { color: "#cbd5e1" },
      type: "scroll",
    },
    grid: { top: 48, right: 18, bottom: 24, left: 20, containLabel: true },
    xAxis: {
      type: "category",
      data: revenueGrowth.labels,
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.18)" } },
      axisLabel: { color: "#94a3b8" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#94a3b8", formatter: (value: number) => `$${Math.round(value / 1000)}k` },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    series: revenueGrowth.series.map((series, index) => ({
      name: series.name,
      type: "line",
      smooth: true,
      stack: "growth",
      showSymbol: false,
      areaStyle: { opacity: 0.2 },
      lineStyle: { width: 2 },
      color: ["#6366f1", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444"][index % 5],
      data: series.data,
    })),
  };

  const toggleRegion = (regionId: string) => {
    setSelectedRegions((current) =>
      current.includes(regionId) ? current.filter((value) => value !== regionId) : [...current, regionId],
    );
  };

  return (
    <div className="space-y-6">
      <section className="panel-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="eyebrow">Filters</p>
            <h3 className="mt-2 text-xl font-semibold text-white">Analytics Controls</h3>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {selectedRegions.length ? <StatusBadge label={`${selectedRegions.length} regions`} variant="cyan" /> : <StatusBadge label="All regions" variant="slate" />}
            <StatusBadge label={selectedCategory === "all" ? "All categories" : selectedCategory} variant="indigo" />
          </div>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(240px,1.2fr)_repeat(2,minmax(0,0.75fr))_minmax(220px,0.9fr)]">
          <details className="group relative">
            <summary className="input-shell flex cursor-pointer list-none items-center justify-between gap-3">
              <span className="truncate">
                {selectedRegions.length
                  ? `${selectedRegions.length} region${selectedRegions.length > 1 ? "s" : ""} selected`
                  : "Select regions"}
              </span>
              <ChevronsUpDown className="h-4 w-4 text-slate-500 transition group-open:rotate-180" />
            </summary>
            <div className="absolute left-0 z-10 mt-2 w-full min-w-[260px] rounded-[24px] border border-white/10 bg-app-surface/95 p-4 shadow-panel backdrop-blur">
              <div className="mb-3 flex items-center justify-between text-xs uppercase tracking-[0.24em] text-slate-400">
                <button type="button" onClick={() => setSelectedRegions(filterOptions.regions.map((region) => region.region_id))}>
                  All
                </button>
                <button type="button" onClick={() => setSelectedRegions([])}>
                  Clear
                </button>
              </div>
              <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                {filterOptions.regions.map((region) => {
                  const checked = selectedRegions.includes(region.region_id);
                  return (
                    <label key={region.region_id} className="flex cursor-pointer items-center justify-between rounded-2xl border border-white/10 bg-slate-950/45 px-3 py-3 text-sm text-slate-200 transition hover:bg-white/5">
                      <span>{region.region_name}</span>
                      <span
                        className={`inline-flex h-5 w-5 items-center justify-center rounded-full border ${checked ? "border-cyan-400/40 bg-cyan-400/20 text-cyan-100" : "border-white/10 text-transparent"}`}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </span>
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={checked}
                        onChange={() => toggleRegion(region.region_id)}
                      />
                    </label>
                  );
                })}
              </div>
            </div>
          </details>

          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-[0.24em] text-slate-400">Start date</span>
            <input className="input-shell" type="date" value={startDate} max={endDate} onChange={(event) => setStartDate(event.target.value)} />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-[0.24em] text-slate-400">End date</span>
            <input className="input-shell" type="date" value={endDate} min={startDate} onChange={(event) => setEndDate(event.target.value)} />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs uppercase tracking-[0.24em] text-slate-400">Product category</span>
            <select className="input-shell" value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
              <option value="all">All categories</option>
              {filterOptions.categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          title="Sales Volume Heatmap"
          subtitle="Units sold by region and day of week across the active date range."
        >
          {heatmap.regions.length ? <EChart option={heatmapOption} height={340} /> : <NoDataState message="No sales records match the selected filters." />}
        </SectionCard>

        <SectionCard
          title="Inventory Turnover Ratio"
          subtitle="Six-month turnover trend for the strongest products in the selected category."
        >
          {turnoverSeries.series.length ? (
            <EChart option={turnoverOption} height={340} />
          ) : (
            <NoDataState message="No turnover data is available for the selected category." />
          )}
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          title="Supplier Reliability"
          subtitle="Suppliers sorted from worst to best on-time delivery performance."
        >
          {supplierRows.length ? <EChart option={supplierOption} height={340} /> : <NoDataState message="No supplier reliability data is available." />}
        </SectionCard>

        <SectionCard
          title="Revenue Growth By Region"
          subtitle="Stacked month-over-month revenue delta per region over the active date range."
        >
          {revenueGrowth.series.length ? (
            <EChart option={revenueGrowthOption} height={340} />
          ) : (
            <NoDataState message="No revenue growth series can be built from the selected dates." />
          )}
        </SectionCard>
      </section>
    </div>
  );
}
