"use client";

import { useState } from "react";

import { useSessionContext } from "@/context/session-context";
import { fetchForecastHistory, generateForecast } from "@/lib/api";
import type { ForecastHistoryResponse, ForecastRecordResponse, InventoryPositionItem } from "@/types";

interface ForecastWorkspaceProps {
  positions: InventoryPositionItem[];
}

/** Creates a stable option label for a product-region forecast scope. */
function buildScopeLabel(position: InventoryPositionItem): string {
  return `${position.product_name} - ${position.region_name}`;
}

export function ForecastWorkspace({ positions }: ForecastWorkspaceProps) {
  const session = useSessionContext();
  const scopes = positions.map((position) => ({
    key: `${position.product_id}:${position.region_id}`,
    label: buildScopeLabel(position),
    productId: position.product_id,
    regionId: position.region_id,
  }));

  const [selectedScope, setSelectedScope] = useState<string>(scopes[0]?.key ?? "");
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
      const token = await session.getToken();
      const forecast = await generateForecast(
        {
          product_id: resolvedScope.productId,
          region_id: resolvedScope.regionId,
        },
        token,
      );
      const historyResponse = await fetchForecastHistory(resolvedScope.productId, token);
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
          Select a product-region scope and persist a seven-day model-backed forecast with explanation details.
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
                <p className="text-sm text-slate-400">7-day demand</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.forecast_json.summary.total_units}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Avg Daily Units</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.forecast_json.summary.avg_daily_units}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Stockout probability</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.forecast_json.summary.stockout_risk_pct}%</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-slate-400">Recommended reorder</p>
                <p className="mt-2 text-2xl font-semibold text-white">{latestForecast.forecast_json.summary.recommended_reorder_units}</p>
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
                        {item.region_name} - {item.forecast_json.horizon_days} day horizon
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-slate-400">Generated</p>
                      <p className="text-sm text-white">{new Date(item.run_at).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Demand</p>
                      <p className="mt-1 text-lg font-semibold text-white">{item.forecast_json.summary.total_units}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Reorder</p>
                      <p className="mt-1 text-lg font-semibold text-white">{item.forecast_json.summary.recommended_reorder_units}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Risk</p>
                      <p className="mt-1 text-lg font-semibold text-white">{item.forecast_json.summary.stockout_risk_pct}%</p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {item.shap_json.top_features.slice(0, 4).map((feature) => (
                      <div key={`${item.forecast_id}-${feature.feature}`} className="rounded-xl border border-white/10 bg-slate-900/40 p-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{feature.feature}</p>
                        <p className="mt-1 text-sm font-medium text-white">{feature.contribution}</p>
                      </div>
                    ))}
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
