"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="h-80 animate-pulse rounded-lg bg-slate-800" />,
});

const REGION_OPTIONS = [
  { id: "chicago", label: "Chicago Cross-Dock" },
  { id: "dallas", label: "Dallas Distribution Center" },
  { id: "los-angeles", label: "Los Angeles Fulfillment Hub" },
  { id: "north-hub", label: "North Hub" },
  { id: "south-hub", label: "South Hub" },
];

const CATEGORY_OPTIONS = ["all", "Cold Chain", "Packaging", "Automation"];
const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTH_LABELS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];

const HEATMAP_VALUES: Record<string, number[]> = {
  chicago: [182, 224, 265, 301, 328, 278, 240],
  dallas: [210, 246, 288, 344, 392, 318, 274],
  "los-angeles": [254, 296, 342, 388, 430, 356, 308],
  "north-hub": [164, 196, 232, 268, 284, 238, 214],
  "south-hub": [140, 178, 208, 246, 264, 220, 194],
};

const TURNOVER_SERIES = [
  { name: "Cold Chain", values: [4.2, 4.8, 5.1, 5.7, 6.2, 6.8] },
  { name: "Packaging", values: [3.1, 3.4, 3.8, 4.0, 4.4, 4.9] },
  { name: "Automation", values: [2.3, 2.9, 3.4, 3.8, 4.2, 4.6] },
];

const SUPPLIER_RELIABILITY = [
  { supplier: "Gamma Logistics", reliability: 62 },
  { supplier: "Beta Micro Devices", reliability: 74 },
  { supplier: "Northstar Components", reliability: 83 },
  { supplier: "Alpha Plastics", reliability: 91 },
  { supplier: "Apex Sensors", reliability: 97 },
];

const REVENUE_GROWTH_SERIES = [
  { id: "chicago", name: "Chicago Cross-Dock", values: [18, 21, 24, 26, 29, 32] },
  { id: "dallas", name: "Dallas Distribution Center", values: [15, 18, 22, 24, 27, 30] },
  { id: "los-angeles", name: "Los Angeles Fulfillment Hub", values: [22, 26, 29, 33, 36, 39] },
  { id: "north-hub", name: "North Hub", values: [10, 12, 14, 17, 20, 22] },
  { id: "south-hub", name: "South Hub", values: [8, 10, 13, 15, 17, 19] },
];

function buildHeatmapOption(regionIds: string[]) {
  const activeRegions =
    regionIds.length > 0
      ? REGION_OPTIONS.filter((region) => regionIds.includes(region.id))
      : REGION_OPTIONS;

  return {
    tooltip: {
      position: "top",
    },
    grid: {
      top: 16,
      right: 20,
      bottom: 28,
      left: 120,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: WEEKDAY_LABELS,
      axisLabel: { color: "#cbd5e1" },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: activeRegions.map((region) => region.label),
      axisLabel: { color: "#cbd5e1" },
      splitArea: { show: true },
    },
    visualMap: {
      min: 100,
      max: 500,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      textStyle: { color: "#cbd5e1" },
      inRange: {
        color: ["#1e3a5f", "#06b6d4"],
      },
    },
    series: [
      {
        type: "heatmap",
        data: activeRegions.flatMap((region, regionIndex) =>
          HEATMAP_VALUES[region.id].map((value, dayIndex) => [dayIndex, regionIndex, value]),
        ),
        label: {
          show: true,
          color: "#e2e8f0",
        },
      },
    ],
  };
}

function buildTurnoverOption(category: string) {
  const activeSeries =
    category === "all"
      ? TURNOVER_SERIES
      : TURNOVER_SERIES.filter((series) => series.name === category);

  return {
    tooltip: {
      trigger: "axis",
    },
    legend: {
      textStyle: { color: "#cbd5e1" },
    },
    grid: {
      top: 40,
      right: 20,
      bottom: 24,
      left: 48,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: MONTH_LABELS,
      axisLabel: { color: "#cbd5e1" },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 10,
      axisLabel: { color: "#94a3b8" },
      splitLine: {
        lineStyle: { color: "rgba(148,163,184,0.12)" },
      },
    },
    series: activeSeries.map((series) => ({
      name: series.name,
      type: "line",
      smooth: true,
      symbolSize: 10,
      data: series.values,
      areaStyle: { opacity: 0.08 },
    })),
  };
}

function buildSupplierOption() {
  const rows = [...SUPPLIER_RELIABILITY].sort((left, right) => left.reliability - right.reliability);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: {
      top: 16,
      right: 20,
      bottom: 24,
      left: 160,
      containLabel: true,
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: {
        color: "#94a3b8",
        formatter: "{value}%",
      },
      splitLine: {
        lineStyle: { color: "rgba(148,163,184,0.12)" },
      },
    },
    yAxis: {
      type: "category",
      data: rows.map((row) => row.supplier),
      axisLabel: { color: "#cbd5e1" },
    },
    series: [
      {
        type: "bar",
        data: rows.map((row) => ({
          value: row.reliability,
          itemStyle: {
            color: row.reliability < 70 ? "#ef4444" : row.reliability <= 85 ? "#f59e0b" : "#22c55e",
            borderRadius: [8, 8, 8, 8],
          },
        })),
      },
    ],
  };
}

function buildRevenueOption(regionIds: string[]) {
  const activeSeries =
    regionIds.length > 0
      ? REVENUE_GROWTH_SERIES.filter((series) => regionIds.includes(series.id))
      : REVENUE_GROWTH_SERIES;

  return {
    tooltip: {
      trigger: "axis",
    },
    legend: {
      textStyle: { color: "#cbd5e1" },
    },
    grid: {
      top: 40,
      right: 20,
      bottom: 24,
      left: 48,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: MONTH_LABELS,
      axisLabel: { color: "#cbd5e1" },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#94a3b8",
        formatter: "{value}%",
      },
      splitLine: {
        lineStyle: { color: "rgba(148,163,184,0.12)" },
      },
    },
    series: activeSeries.map((series) => ({
      name: series.name,
      type: "line",
      stack: "growth",
      smooth: true,
      areaStyle: { opacity: 0.16 },
      data: series.values,
    })),
  };
}

function ChartShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: JSX.Element;
}) {
  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
      <div className="mb-5">
        <h2 className="text-xl font-semibold text-white">{title}</h2>
        <p className="mt-2 text-sm text-slate-400">{description}</p>
      </div>
      {children}
    </section>
  );
}

export default function AnalyticsPage() {
  const [selectedRegions, setSelectedRegions] = useState<string[]>(REGION_OPTIONS.map((region) => region.id));
  const [startDate, setStartDate] = useState("2025-12-27");
  const [endDate, setEndDate] = useState("2026-03-26");
  const [selectedCategory, setSelectedCategory] = useState("all");

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-white">Analytics Studio</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              Static rendering-safe analytics preview with plain HTML filters and SSR-safe ECharts mounts.
            </p>
          </div>
          <div className="inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200">
            Mock Data Preview
          </div>
        </div>

        <div className="mt-6 grid gap-4 xl:grid-cols-[1.3fr_1fr_0.9fr]">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">Regions</span>
            <select
              multiple
              value={selectedRegions}
              onChange={(event) =>
                setSelectedRegions(Array.from(event.currentTarget.selectedOptions, (option) => option.value))
              }
              className="h-40 w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/40"
            >
              {REGION_OPTIONS.map((region) => (
                <option key={region.id} value={region.id}>
                  {region.label}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">Hold Ctrl or Command to select multiple regions.</p>
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-300">Start date</span>
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.currentTarget.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/40"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-300">End date</span>
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.currentTarget.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/40"
              />
            </label>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">Category</span>
            <select
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.currentTarget.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/40"
            >
              <option value="all">All categories</option>
              {CATEGORY_OPTIONS.filter((category) => category !== "all").map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              Mock filters currently drive chart previews only. API data will be reconnected after rendering is stable.
            </p>
          </label>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <ChartShell
          title="Sales Heatmap"
          description={`Sales volume by region and day-of-week for ${startDate} to ${endDate}.`}
        >
          <ReactECharts option={buildHeatmapOption(selectedRegions)} style={{ height: 340 }} />
        </ChartShell>

        <ChartShell
          title="Inventory Turnover"
          description="Six-month turnover ratio preview across product lines."
        >
          <ReactECharts option={buildTurnoverOption(selectedCategory)} style={{ height: 340 }} />
        </ChartShell>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_minmax(0,1.05fr)]">
        <ChartShell
          title="Supplier Reliability"
          description="Horizontal ranking of suppliers from worst to best on-time performance."
        >
          <ReactECharts option={buildSupplierOption()} style={{ height: 340 }} />
        </ChartShell>

        <ChartShell
          title="Revenue Growth"
          description="Stacked area view of month-over-month regional revenue growth."
        >
          <ReactECharts option={buildRevenueOption(selectedRegions)} style={{ height: 340 }} />
        </ChartShell>
      </div>
    </div>
  );
}
