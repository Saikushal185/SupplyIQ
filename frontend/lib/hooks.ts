"use client";

import useSWR from "swr";

import { useSessionContext } from "@/context/session-context";
import {
  fetchForecastHistory,
  fetchInventorySummary,
  fetchInventoryTurnover,
  fetchLatestForecast,
  fetchLowStock,
  fetchPipelineStatus,
  fetchRegionalGrowth,
  fetchSalesAnalytics,
  fetchSupplierReliability,
} from "@/lib/api";
import type {
  ApiEnvelope,
  ForecastRecordResponse,
  InventoryPositionItem,
  InventoryTurnoverItem,
  PipelineStatus,
  RegionalGrowthItem,
  SalesAnalyticsItem,
  SupplierPerformanceItem,
} from "@/types";

type SwrKey = ReadonlyArray<string | number | boolean | null | undefined>;

/** Creates an SWR query tied to the current session token context. */
function useAuthedQuery<T>(key: SwrKey, fetcher: (token: string | null) => Promise<ApiEnvelope<T>>) {
  const session = useSessionContext();
  const swrKey = session.isLoaded ? [...key, session.userId ?? "guest"] : null;

  return useSWR(swrKey, async () => fetcher(await session.getToken()));
}

function useOptionalAuthedQuery<T>(key: SwrKey, fetcher: (token: string | null) => Promise<ApiEnvelope<T> | null>) {
  const session = useSessionContext();
  const swrKey = session.isLoaded ? [...key, session.userId ?? "guest"] : null;

  return useSWR(swrKey, async () => fetcher(await session.getToken()));
}

export function useInventorySummary(regionId?: string) {
  return useAuthedQuery<InventoryPositionItem[]>(["inventory-summary", regionId], (token) =>
    fetchInventorySummary(regionId, token),
  );
}

export function useLowStock(regionId?: string) {
  return useAuthedQuery<InventoryPositionItem[]>(["low-stock", regionId], (token) => fetchLowStock(regionId, token));
}

export function useSalesAnalytics(startDate?: string, endDate?: string, regionId?: string) {
  return useAuthedQuery<SalesAnalyticsItem[]>(["sales-analytics", startDate, endDate, regionId], (token) =>
    fetchSalesAnalytics(startDate, endDate, regionId, token),
  );
}

export function useInventoryTurnover(startDate?: string, endDate?: string) {
  return useAuthedQuery<InventoryTurnoverItem[]>(["inventory-turnover", startDate, endDate], (token) =>
    fetchInventoryTurnover(startDate, endDate, token),
  );
}

export function useSupplierReliability(regionId?: string) {
  return useAuthedQuery<SupplierPerformanceItem[]>(["supplier-reliability", regionId], (token) =>
    fetchSupplierReliability(regionId, token),
  );
}

export function useRegionalGrowth() {
  return useAuthedQuery<RegionalGrowthItem[]>(["regional-growth"], (token) => fetchRegionalGrowth(token));
}

export function useLatestForecast(productId: string | null, regionId: string | null) {
  const shouldFetch = Boolean(productId && regionId);
  return useOptionalAuthedQuery<ForecastRecordResponse>(["latest-forecast", productId, regionId, shouldFetch], async (token) => {
    if (!productId || !regionId) {
      return null;
    }
    return fetchLatestForecast(productId, regionId, token);
  });
}

export function useForecastHistory(productId: string | null) {
  const shouldFetch = Boolean(productId);
  return useOptionalAuthedQuery<ForecastRecordResponse[]>(["forecast-history", productId, shouldFetch], async (token) => {
    if (!productId) {
      return null;
    }
    return fetchForecastHistory(productId, token);
  });
}

export function usePipelineStatus() {
  return useAuthedQuery<PipelineStatus>(["pipeline-status"], (token) => fetchPipelineStatus(token));
}
