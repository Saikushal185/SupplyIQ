"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useUser } from "@clerk/nextjs";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="h-80 animate-pulse rounded-lg bg-slate-800" />,
});

const MOCK_PRODUCTS = [
  { id: "cold-chain-sensor", label: "Cold Chain Sensor" },
  { id: "packing-tape-roll", label: "Packing Tape Roll" },
  { id: "smart-label-printer", label: "Smart Label Printer" },
];

const MOCK_REGIONS = [
  { id: "chicago", label: "Chicago Cross-Dock" },
  { id: "dallas", label: "Dallas Distribution Center" },
  { id: "los-angeles", label: "Los Angeles Fulfillment Hub" },
  { id: "south-hub", label: "South Hub" },
];

interface MockForecastState {
  lastRun: string;
  stockoutRiskDetected: boolean;
  stockoutRiskLabel: string;
  forecastPoints: Array<{ label: string; forecast: number; lower: number; upper: number }>;
  shapPoints: Array<{ feature: string; contribution: number }>;
}

function buildMockForecast(productId: string, regionId: string): MockForecastState {
  const base = productId.length + regionId.length;
  const forecastPoints = [
    { label: "Day 1", forecast: 112 + base, lower: 102 + base, upper: 124 + base },
    { label: "Day 2", forecast: 118 + base, lower: 106 + base, upper: 131 + base },
    { label: "Day 3", forecast: 125 + base, lower: 111 + base, upper: 139 + base },
    { label: "Day 4", forecast: 132 + base, lower: 118 + base, upper: 147 + base },
    { label: "Day 5", forecast: 129 + base, lower: 116 + base, upper: 143 + base },
    { label: "Day 6", forecast: 138 + base, lower: 123 + base, upper: 154 + base },
    { label: "Day 7", forecast: 144 + base, lower: 128 + base, upper: 160 + base },
  ];

  const shapPoints = [
    { feature: "traffic_index", contribution: 0.82 },
    { feature: "rolling_7d_avg", contribution: 0.69 },
    { feature: "weather_temp", contribution: 0.41 },
    { feature: "promo_calendar", contribution: -0.32 },
    { feature: "supplier_delay", contribution: -0.46 },
  ];

  const stockoutRiskDetected = productId === "smart-label-printer" || regionId === "south-hub";

  return {
    lastRun: new Date().toLocaleString(),
    stockoutRiskDetected,
    stockoutRiskLabel: stockoutRiskDetected ? "Stockout risk detected within the next 7 days." : "No near-term stockout risk detected.",
    forecastPoints,
    shapPoints,
  };
}

function buildForecastOption(forecast: MockForecastState) {
  const lowers = forecast.forecastPoints.map((point) => point.lower);

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
      data: forecast.forecastPoints.map((point) => point.label),
      axisLabel: { color: "#cbd5e1" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    series: [
      {
        name: "Lower bound",
        type: "line",
        data: lowers,
        stack: "confidence",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
      },
      {
        name: "Confidence band",
        type: "line",
        data: forecast.forecastPoints.map((point, index) => point.upper - lowers[index]),
        stack: "confidence",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(99, 102, 241, 0.16)" },
      },
      {
        name: "Forecast",
        type: "line",
        smooth: true,
        data: forecast.forecastPoints.map((point) => point.forecast),
        lineStyle: { width: 3, color: "#818cf8" },
        itemStyle: { color: "#a5b4fc" },
      },
    ],
  };
}

function buildShapOption(forecast: MockForecastState) {
  const rows = [...forecast.shapPoints].reverse();

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
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    yAxis: {
      type: "category",
      data: rows.map((row) => row.feature),
      axisLabel: { color: "#cbd5e1" },
    },
    series: [
      {
        type: "bar",
        data: rows.map((row) => ({
          value: row.contribution,
          itemStyle: {
            color: row.contribution < 0 ? "#fb923c" : "#22c55e",
            borderRadius: [8, 8, 8, 8],
          },
        })),
      },
    ],
  };
}

export default function ForecastPage() {
  const { user, isLoaded } = useUser();
  const role = typeof user?.publicMetadata?.role === "string" ? user.publicMetadata.role : "viewer";

  const [selectedProductId, setSelectedProductId] = useState(MOCK_PRODUCTS[0].id);
  const [selectedRegionId, setSelectedRegionId] = useState(MOCK_REGIONS[0].id);
  const [isGenerating, setIsGenerating] = useState(false);
  const [forecast, setForecast] = useState<MockForecastState | null>(null);
  const [lastRun, setLastRun] = useState("never");

  const handleGenerate = async () => {
    if (role === "viewer") {
      return;
    }

    setIsGenerating(true);
    await new Promise((resolve) => window.setTimeout(resolve, 550));
    const nextForecast = buildMockForecast(selectedProductId, selectedRegionId);
    setForecast(nextForecast);
    setLastRun(nextForecast.lastRun);
    setIsGenerating(false);
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)]">
      <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Forecast Console</h1>
          <p className="mt-2 text-sm text-slate-400">Mock forecast generation flow for stabilizing the client rendering path.</p>
        </div>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">Product</span>
            <select
              value={selectedProductId}
              onChange={(event) => setSelectedProductId(event.currentTarget.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-indigo-400/50"
            >
              {MOCK_PRODUCTS.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">Region</span>
            <select
              value={selectedRegionId}
              onChange={(event) => setSelectedRegionId(event.currentTarget.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-indigo-400/50"
            >
              {MOCK_REGIONS.map((region) => (
                <option key={region.id} value={region.id}>
                  {region.label}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={!isLoaded || role === "viewer" || isGenerating}
            className="w-full rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
          >
            {isGenerating ? "Generating forecast..." : role === "viewer" ? "Viewer access: generation disabled" : "Generate Forecast"}
          </button>

          <p className="text-sm text-slate-400">Last run: {lastRun}</p>
        </div>
      </section>

      <div className="space-y-6">
        {!forecast ? (
          <section className="rounded-3xl border border-dashed border-white/15 bg-slate-950/60 p-8 text-center">
            <h2 className="text-xl font-semibold text-white">Forecast Preview</h2>
            <p className="mt-3 text-sm text-slate-400">Select a product and region, then click Generate Forecast</p>
          </section>
        ) : (
          <>
            {forecast.stockoutRiskDetected ? (
              <div className="rounded-3xl border border-amber-400/30 bg-amber-400/10 px-5 py-4 text-sm text-amber-100">
                {forecast.stockoutRiskLabel}
              </div>
            ) : null}

            <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
              <h2 className="text-xl font-semibold text-white">Demand Forecast</h2>
              <p className="mt-2 text-sm text-slate-400">Projected demand with a confidence band over the next seven days.</p>
              <div className="mt-5">
                <ReactECharts option={buildForecastOption(forecast)} style={{ height: 340 }} />
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
              <h2 className="text-xl font-semibold text-white">SHAP Feature Drivers</h2>
              <p className="mt-2 text-sm text-slate-400">Mock explanatory drivers for the generated forecast.</p>
              <div className="mt-5">
                <ReactECharts option={buildShapOption(forecast)} style={{ height: 300 }} />
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
