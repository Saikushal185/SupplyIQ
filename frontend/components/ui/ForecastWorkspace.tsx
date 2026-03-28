"use client";

import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { LoaderCircle, Search } from "lucide-react";

import { EChart } from "@/components/charts/EChart";
import { SectionCard } from "@/components/ui/SectionCard";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useSessionContext } from "@/context/session-context";
import { generateForecast } from "@/lib/api";
import {
  buildForecastBand,
  buildForecastInsight,
  buildShapSeries,
  findStockoutDate,
  formatDateTime,
  formatShortDate,
} from "@/lib/insights";
import { useLatestForecast } from "@/lib/hooks";
import { getForecastResultState } from "@/lib/view-state";
import type { InventoryPositionItem } from "@/types";

interface ForecastWorkspaceProps {
  positions: InventoryPositionItem[];
}

function ResultSkeleton() {
  return (
    <div className="space-y-6">
      <div className="panel-surface p-6">
        <SkeletonBlock className="h-4 w-40" />
        <SkeletonBlock className="mt-3 h-[320px] w-full rounded-[24px]" />
      </div>
      <div className="panel-surface p-6">
        <SkeletonBlock className="h-4 w-32" />
        <SkeletonBlock className="mt-3 h-[280px] w-full rounded-[24px]" />
      </div>
    </div>
  );
}

function EmptyResultState() {
  return (
    <div className="flex min-h-[320px] items-center justify-center rounded-[24px] border border-dashed border-white/10 bg-slate-950/35 px-6 text-center text-sm text-slate-400">
      Generate a forecast to inspect the next seven days of demand and model explainability.
    </div>
  );
}

export function ForecastWorkspace({ positions }: ForecastWorkspaceProps) {
  const session = useSessionContext();
  const productMap = useMemo(() => {
    const map = new Map<string, { productId: string; productName: string; sku: string; regions: InventoryPositionItem[] }>();
    positions.forEach((position) => {
      const current = map.get(position.product_id) ?? {
        productId: position.product_id,
        productName: position.product_name,
        sku: position.sku,
        regions: [],
      };
      current.regions.push(position);
      map.set(position.product_id, current);
    });
    return [...map.values()].sort((left, right) => left.productName.localeCompare(right.productName));
  }, [positions]);

  const [productQuery, setProductQuery] = useState("");
  const [selectedProductId, setSelectedProductId] = useState(productMap[0]?.productId ?? "");
  const [selectedRegionId, setSelectedRegionId] = useState(productMap[0]?.regions[0]?.region_id ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const selectedProduct = productMap.find((product) => product.productId === selectedProductId) ?? null;
  const availableRegions = useMemo(
    () =>
      selectedProduct?.regions.slice().sort((left, right) => left.region_name.localeCompare(right.region_name)) ?? [],
    [selectedProduct],
  );
  const selectedPosition = availableRegions.find((region) => region.region_id === selectedRegionId) ?? availableRegions[0] ?? null;

  useEffect(() => {
    if (!selectedProduct && productMap[0]) {
      setSelectedProductId(productMap[0].productId);
      setSelectedRegionId(productMap[0].regions[0]?.region_id ?? "");
      return;
    }

    if (selectedProduct && !availableRegions.some((region) => region.region_id === selectedRegionId)) {
      setSelectedRegionId(availableRegions[0]?.region_id ?? "");
    }
  }, [availableRegions, productMap, selectedProduct, selectedRegionId]);

  const latestForecast = useLatestForecast(selectedPosition?.product_id ?? null, selectedPosition?.region_id ?? null);
  const latestForecastData = latestForecast.data?.data ?? null;
  const filteredProducts = productMap.filter((product) => {
    const normalizedQuery = productQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return true;
    }
    return `${product.productName} ${product.sku}`.toLowerCase().includes(normalizedQuery);
  });

  const forecastBand = buildForecastBand(latestForecastData);
  const shapSeries = buildShapSeries(latestForecastData);
  const stockoutDate = selectedPosition ? findStockoutDate(selectedPosition.quantity, latestForecastData) : null;
  const insightLabel = buildForecastInsight(latestForecastData);

  const forecastOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      top: 0,
      textStyle: { color: "#cbd5e1" },
    },
    grid: { top: 46, right: 18, bottom: 24, left: 20, containLabel: true },
    xAxis: {
      type: "category",
      data: forecastBand.labels,
      boundaryGap: false,
      axisLabel: { color: "#94a3b8" },
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.18)" } },
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
        stack: "confidence-band",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        data: forecastBand.lower,
      },
      {
        name: "Confidence band",
        type: "line",
        stack: "confidence-band",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(99,102,241,0.18)" },
        data: forecastBand.upper.map((value, index) => value - (forecastBand.lower[index] ?? 0)),
      },
      {
        name: "Predicted units",
        type: "line",
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3, color: "#06b6d4" },
        itemStyle: { color: "#06b6d4" },
        data: forecastBand.predicted,
      },
    ],
  };

  const shapOption: EChartsOption = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: { top: 18, right: 18, bottom: 24, left: 140 },
    xAxis: {
      type: "value",
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
    },
    yAxis: {
      type: "category",
      data: shapSeries.map((item) => item.displayLabel),
      axisLabel: { color: "#cbd5e1" },
    },
    series: [
      {
        type: "bar",
        data: shapSeries.map((item) => ({
          value: item.value,
          itemStyle: {
            color: item.direction === "up" ? "#22c55e" : "#ef4444",
            borderRadius: [0, 10, 10, 0],
          },
        })),
      },
    ],
  };

  const handleGenerate = async () => {
    if (!selectedPosition) {
      setSubmissionError("Select a product and region before generating a forecast.");
      return;
    }

    if (!session.canGenerateForecast) {
      setSubmissionError("Viewer roles can review forecasts but cannot generate them.");
      return;
    }

    setIsSubmitting(true);
    setSubmissionError(null);
    try {
      const token = await session.getToken();
      const response = await generateForecast(
        {
          product_id: selectedPosition.product_id,
          region_id: selectedPosition.region_id,
        },
        token,
      );
      await latestForecast.mutate(response, { revalidate: false });
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : "Unable to generate a forecast right now.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const forecastResultState = getForecastResultState({
    hasSelectedPosition: Boolean(selectedPosition),
    isLoading: latestForecast.isLoading,
    hasError: Boolean(latestForecast.error),
    hasData: Boolean(latestForecastData),
  });
  const resolvedForecast = forecastResultState === "result" ? latestForecastData : null;

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="panel-surface p-5 md:p-6">
        <p className="eyebrow">Forecast Scope</p>
        <h3 className="mt-2 text-2xl font-semibold text-white">Select product and region</h3>
        <p className="mt-3 text-sm text-slate-400">
          Search a product, choose its region, then generate a seven-day demand forecast with confidence bounds and SHAP insights.
        </p>

        <div className="mt-6 space-y-5">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-slate-400">Product</label>
            <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-3">
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  className="input-shell pl-11"
                  placeholder="Search product name or SKU"
                  value={productQuery}
                  onChange={(event) => setProductQuery(event.target.value)}
                />
              </div>
              <div className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
                {filteredProducts.map((product) => {
                  const active = product.productId === selectedProductId;
                  return (
                    <button
                      key={product.productId}
                      type="button"
                      className={`w-full rounded-2xl border px-4 py-3 text-left transition ${active ? "border-indigo-400/30 bg-indigo-400/15 text-white" : "border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"}`}
                      onClick={() => setSelectedProductId(product.productId)}
                    >
                      <p className="font-medium">{product.productName}</p>
                      <p className="mono-data mt-1 text-xs text-slate-400">{product.sku}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-slate-400">Region</label>
            <select
              className="input-shell"
              value={selectedRegionId}
              onChange={(event) => setSelectedRegionId(event.target.value)}
              disabled={!availableRegions.length}
            >
              {availableRegions.map((region) => (
                <option key={region.region_id} value={region.region_id}>
                  {region.region_name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
            onClick={handleGenerate}
            disabled={!session.canGenerateForecast || isSubmitting || !selectedPosition}
          >
            {isSubmitting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
            {isSubmitting ? "Generating forecast..." : "Generate 7-Day Forecast"}
          </button>

          <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Last forecast run</p>
            <p className="mono-data mt-2 text-sm text-white">{formatDateTime(latestForecastData?.run_at ?? null)}</p>
          </div>

          {!session.canGenerateForecast ? (
            <div className="rounded-[24px] border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-100">
              Viewer role detected. You can review the latest saved forecast, but generation is disabled.
            </div>
          ) : null}

          {submissionError ? <p className="text-sm text-rose-300">{submissionError}</p> : null}
        </div>
      </div>

      <div className="space-y-6">
        {stockoutDate ? (
          <div className="rounded-[28px] border border-amber-400/20 bg-amber-400/10 p-5 text-amber-100">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-amber-100/80">Stockout risk detected</p>
                <h4 className="mt-2 text-xl font-semibold text-white">{selectedPosition?.product_name}</h4>
                <p className="mt-2 text-sm text-amber-50/90">
                  Forecasted demand suggests this region could stock out by {formatShortDate(stockoutDate)} if no replenishment arrives.
                </p>
              </div>
              <StatusBadge label={formatShortDate(stockoutDate)} variant="amber" />
            </div>
          </div>
        ) : null}

        {forecastResultState === "loading" ? (
          <ResultSkeleton />
        ) : forecastResultState === "error" ? (
          <div className="panel-surface p-6 text-rose-100">
            Unable to load the latest forecast for the selected scope.
          </div>
        ) : forecastResultState === "result" ? (
          <>
            <SectionCard
              title="Forecast Confidence Band"
              subtitle={`Predicted units sold for ${selectedPosition?.product_name ?? "the selected product"} in ${selectedPosition?.region_name ?? "the selected region"}.`}
              action={<StatusBadge label={`${resolvedForecast!.forecast_json.horizon_days} days`} variant="cyan" />}
            >
              <EChart option={forecastOption} height={340} />
              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
                  <p className="text-sm text-slate-400">Predicted units</p>
                  <p className="mono-data mt-2 text-2xl text-white">{resolvedForecast!.forecast_json.summary.total_units}</p>
                </div>
                <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
                  <p className="text-sm text-slate-400">Avg daily demand</p>
                  <p className="mono-data mt-2 text-2xl text-white">{resolvedForecast!.forecast_json.summary.avg_daily_units}</p>
                </div>
                <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
                  <p className="text-sm text-slate-400">Recommended reorder</p>
                  <p className="mono-data mt-2 text-2xl text-white">{resolvedForecast!.forecast_json.summary.recommended_reorder_units}</p>
                </div>
              </div>
            </SectionCard>

            <SectionCard
              title="SHAP Explainability"
              subtitle="Top features influencing the current forecast outcome."
            >
              <EChart option={shapOption} height={300} />
              <div className="mt-5 rounded-[24px] border border-emerald-400/15 bg-emerald-400/10 p-4 text-sm text-emerald-100">
                {insightLabel}
              </div>
            </SectionCard>
          </>
        ) : (
          <SectionCard
            title="Forecast Results"
            subtitle="Results will populate here after a forecast is generated for the selected scope."
          >
            <EmptyResultState />
          </SectionCard>
        )}
      </div>
    </div>
  );
}
