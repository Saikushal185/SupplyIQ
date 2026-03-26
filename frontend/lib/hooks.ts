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
  ApiResponse,
  ForecastRecordResponse,
  InventorySummaryItem,
  InventoryTurnoverItem,
  PipelineStatusItem,
  RegionalGrowthItem,
  SalesAnalyticsItem,
  SupplierReliabilityItem,
} from "@/types";

type SwrKey = ReadonlyArray<string | number | boolean | null | undefined>;

function useAuthedQuery<T>(key: SwrKey, fetcher: (token: string | null) => Promise<ApiResponse<T>>) {
  const session = useSessionContext();

  return useSWR([...key, session.userId ?? "guest"], async () => fetcher(await session.getToken()));
}

export function useInventorySummary(regionId?: string) {
  return useAuthedQuery<InventorySummaryItem[]>(["inventory-summary", regionId], (token) =>
    fetchInventorySummary(regionId, token),
  );
}

export function useLowStock(regionId?: string) {
  return useAuthedQuery<InventorySummaryItem[]>(["inventory-low-stock", regionId], (token) =>
    fetchLowStock(regionId, token),
  );
}

export function useSalesAnalytics(params?: { startDate?: string; endDate?: string; regionId?: string }) {
  return useAuthedQuery<SalesAnalyticsItem[]>(
    ["sales-analytics", params?.startDate, params?.endDate, params?.regionId],
    (token) => fetchSalesAnalytics(params, token),
  );
}

export function useInventoryTurnover(params?: { startDate?: string; endDate?: string }) {
  return useAuthedQuery<InventoryTurnoverItem[]>(["inventory-turnover", params?.startDate, params?.endDate], (token) =>
    fetchInventoryTurnover(params, token),
  );
}

export function useSupplierReliability() {
  return useAuthedQuery<SupplierReliabilityItem[]>(["supplier-reliability"], (token) =>
    fetchSupplierReliability(token),
  );
}

export function useRegionalGrowth() {
  return useAuthedQuery<RegionalGrowthItem[]>(["regional-growth"], (token) => fetchRegionalGrowth(token));
}

export function useLatestForecast(productId: string | null, regionId: string | null) {
  const shouldFetch = Boolean(productId && regionId);
  return useAuthedQuery<ForecastRecordResponse | null>(
    ["latest-forecast", productId, regionId, shouldFetch],
    async (token) => {
      if (!productId || !regionId) {
        return {
          data: null,
          meta: {
            timestamp: new Date().toISOString(),
            cached: false,
          },
        };
      }
      return fetchLatestForecast(productId, regionId, token);
    },
  );
}

export function useForecastHistory(productId: string | null) {
  const shouldFetch = Boolean(productId);
  return useAuthedQuery<ForecastRecordResponse[]>(
    ["forecast-history", productId, shouldFetch],
    async (token) => {
      if (!productId) {
        return {
          data: [],
          meta: {
            timestamp: new Date().toISOString(),
            cached: false,
          },
        };
      }
      return fetchForecastHistory(productId, token);
    },
  );
}

export function usePipelineStatus() {
  return useAuthedQuery<PipelineStatusItem>(["pipeline-status"], (token) => fetchPipelineStatus(token));
}
