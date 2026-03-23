"use client";

import useSWR from "swr";

import { useSessionContext } from "@/context/session-context";
import {
  fetchAlerts,
  fetchAnalyticsOverview,
  fetchForecastHistory,
  fetchInventoryPositions,
  fetchLatestForecast,
  fetchStockouts,
  fetchSupplierPerformance,
} from "@/lib/api";
import type {
  AlertListResponse,
  AnalyticsOverviewResponse,
  ForecastHistoryResponse,
  ForecastRecordResponse,
  InventoryPositionResponse,
  SupplierPerformanceResponse,
} from "@/types";

type SwrKey = ReadonlyArray<string | number | boolean | null | undefined>;

/** Creates an SWR query tied to the current session token context. */
function useAuthedQuery<T>(key: SwrKey, fetcher: (token: string | null) => Promise<T>) {
  const session = useSessionContext();

  return useSWR([...key, session.userId ?? "guest"], async () => fetcher(await session.getToken()));
}

export function useAnalyticsOverview(regionCode?: string) {
  return useAuthedQuery<AnalyticsOverviewResponse>(["analytics-overview", regionCode], (token) =>
    fetchAnalyticsOverview(regionCode, token),
  );
}

export function useAlerts(regionCode?: string) {
  return useAuthedQuery<AlertListResponse>(["alerts", regionCode], (token) => fetchAlerts(regionCode, token));
}

export function useStockouts(regionCode?: string) {
  return useAuthedQuery<InventoryPositionResponse>(["stockouts", regionCode], (token) =>
    fetchStockouts(regionCode, token),
  );
}

export function useSupplierPerformance(regionCode?: string) {
  return useAuthedQuery<SupplierPerformanceResponse>(["supplier-performance", regionCode], (token) =>
    fetchSupplierPerformance(regionCode, token),
  );
}

export function useInventoryPositions(regionCode?: string, belowReorderOnly = false) {
  return useAuthedQuery<InventoryPositionResponse>(["inventory-positions", regionCode, belowReorderOnly], (token) =>
    fetchInventoryPositions(regionCode, belowReorderOnly, token),
  );
}

export function useLatestForecast(productId: string | null, regionId: string | null) {
  const shouldFetch = Boolean(productId && regionId);
  return useAuthedQuery<ForecastRecordResponse | null>(
    ["latest-forecast", productId, regionId, shouldFetch],
    async (token) => {
      if (!productId || !regionId) {
        return null;
      }
      return fetchLatestForecast(productId, regionId, token);
    },
  );
}

export function useForecastHistory(productId: string | null) {
  const shouldFetch = Boolean(productId);
  return useAuthedQuery<ForecastHistoryResponse | null>(["forecast-history", productId, shouldFetch], async (token) => {
    if (!productId) {
      return null;
    }
    return fetchForecastHistory(productId, token);
  });
}
