"use client";

import { useState } from "react";

import { generateForecast, fetchForecastHistory } from "@/lib/api";
import type { ForecastHistoryResponse, ForecastRecordResponse, InventoryPositionItem } from "@/types";

interface ForecastWorkspaceProps {
  positions: InventoryPositionItem[];
}

/** Creates a stable option label for a product-region forecast scope. */
function buildScopeLabel(position: InventoryPositionItem): string {
  return `${position.product_name} · ${position.region_name}`;
}

export function ForecastWorkspace({ positions }: ForecastWorkspaceProps) {
  const scopes = positions.map((position) => ({
    key: `${position.product_id}:${position.region_id}`,
    label: buildScopeLabel(position),
    productId: position.product_id,
    regionId: position.region_id,
  }));

  const [selectedScope, setSelectedScope] = useState<string>(scopes[0]?.key ?? "");
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [latestForecast, setLatestForecast] = useState<ForecastRecordResponse | null>(null);
  const [history, setHistory] = useState<ForecastHistoryResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const resolvedScope = scopes.find((scope) => scope.key === selectedScope);

  const handleGenerate = async () => {
    if (!resolvedScope) {
      setError("Select a product and region to generate a forecast.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const forecast = await generateForecast({
        product_id: resolvedScope.productId,
        region_id: resolvedScope.regionId,
        horizon_days: horizonDays,
      });
      const historyResponse = await fetchForecastHistory(resolvedScope.productId);
      setLatestForecast(forecast);
      setHistory(historyResponse);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to generate a forecast.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
        <h3 className="text-lg font-semibold text-white">Generate Forecast</h3>
        <p className="mt-2 text-sm text-slate-400">
          Select a product-region scope, choose a planning horizon, and persist a new model-backed forecast.
        </p>

        <label className="mt-5 block text-sm text-slate-300">
          Forecast scope
          <select
            className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-white"
            value={selectedScope}
            onChange={(event) => setSelectedScope(event.target.value)}
          >
            {scopes.map((scope) => (
              <option key={scope.key} value={scope.key}>
                {scope.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mt-4 block text-sm text-slate-300">
          Horizon days
          <input
            type="number"
            min={1}
            max={90}
            className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-white"
            value={horizonDays}
            onChange={(event) => setHorizonDays(Number(event.target.value))}
          />
        </label>

        <button
          type="button"
          className="mt-5 w-full rounded-2xl bg-teal-400 px-4 py-3 font-medium text-slate-950 transition hover:bg-teal-300"
          disabled={isSubmitting}
          onClick={handleGenerate}
        >
          {isSubmitting ? "Generating..." : "Generate Forecast"}
        </button>

        {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
      </div>

      <div className="grid gap-6">
        <div className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
          <h3 className="text-lg font-semibold text-white">Latest Forecast</h3>
          {latestForecast ? (
            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Predicted demand</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.predicted_demand_units}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Confidence band</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {latestForecast.lower_bound_units} - {latestForecast.upper_bound_units}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Stockout probability</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.stockout_probability_pct}%</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Recommended reorder</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.recommended_reorder_units}</p>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">No forecast generated yet in this session.</p>
          )}
        </div>

        <div className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
          <h3 className="text-lg font-semibold text-white">Forecast History</h3>
          {history?.items.length ? (
            <div className="mt-4 space-y-3">
              {history.items.slice(0, 6).map((item) => (
                <div key={item.forecast_id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-white">{item.product_name}</p>
                      <p className="text-sm text-slate-400">
                        {item.region_name} · {item.horizon_days} day horizon
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-slate-400">Generated</p>
                      <p className="text-sm text-white">{new Date(item.generated_at).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Demand</p>
                      <p className="mt-1 text-lg font-semibold text-white">{item.predicted_demand_units}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Reorder</p>
                      <p className="mt-1 text-lg font-semibold text-white">{item.recommended_reorder_units}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Risk</p>
                      <p className="mt-1 text-lg font-semibold text-white">{item.stockout_probability_pct}%</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">Forecast history will appear here after generation.</p>
          )}
        </div>
      </div>
    </div>
  );
}
