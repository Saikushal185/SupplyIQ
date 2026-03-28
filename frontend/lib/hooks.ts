"use client";

import useSWR from "swr";

import { useSessionContext } from "@/context/session-context";
import {
  fetchAnalyticsFilters,
  fetchForecastHistory,
  fetchForecastRunCount,
  fetchInventorySummary,
  fetchInventoryTurnover,
  fetchLatestForecast,
  fetchLowStock,
  fetchPipelineStatus,
  fetchProductSales,
  fetchRegionalGrowth,
  fetchSalesAnalytics,
  fetchSupplierReliability,
} from "@/lib/api";
import type {
  AnalyticsFilterOptions,
  ApiEnvelope,
  ForecastRecordResponse,
  ForecastRunCount,
  InventoryPositionItem,
  InventoryTurnoverItem,
  InventoryTurnoverTrendBucket,
  InventoryTurnoverTrendPeriod,
  PipelineStatus,
  ProductSalesSummaryItem,
  RegionalGrowthItem,
  SalesAnalyticsItem,
  SupplierPerformanceItem,
} from "@/types";

type SwrKey = ReadonlyArray<string | number | boolean | null | undefined>;

/** Creates an SWR query tied to the current session token context. */
function useAuthedQuery<T>(
  key: SwrKey,
  fetcher: (token: string | null) => Promise<ApiEnvelope<T>>,
  enabled = true,
) {
  const session = useSessionContext();
  const swrKey = session.isLoaded && enabled ? [...key, session.userId ?? "guest"] : null;

  return useSWR<ApiEnvelope<T>>(swrKey, async () => fetcher(await session.getToken()));
}

function useOptionalAuthedQuery<T>(
  key: SwrKey,
  fetcher: (token: string | null) => Promise<ApiEnvelope<T> | null>,
  enabled = true,
) {
  const session = useSessionContext();
  const swrKey = session.isLoaded && enabled ? [...key, session.userId ?? "guest"] : null;

  return useSWR<ApiEnvelope<T> | null>(swrKey, async () => fetcher(await session.getToken()));
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

export function useAnalyticsFilters() {
  return useAuthedQuery<AnalyticsFilterOptions>(["analytics-filters"], (token) => fetchAnalyticsFilters(token));
}

export function useProductSales(startDate?: string, endDate?: string, regionId?: string, category?: string) {
  return useAuthedQuery<ProductSalesSummaryItem[]>(["product-sales", startDate, endDate, regionId, category], (token) =>
    fetchProductSales(startDate, endDate, regionId, category, token),
  );
}

export function useForecastRunCount(runDate?: string) {
  return useAuthedQuery<ForecastRunCount>(["forecast-run-count", runDate], (token) => fetchForecastRunCount(runDate, token));
}

export function useInventoryTurnover(startDate?: string, endDate?: string) {
  return useAuthedQuery<InventoryTurnoverItem[]>(["inventory-turnover", startDate, endDate], (token) =>
    fetchInventoryTurnover(startDate, endDate, token),
  );
}

export function useInventoryTurnoverTrend(periods: InventoryTurnoverTrendPeriod[]) {
  const session = useSessionContext();
  const swrKey =
    session.isLoaded && periods.length
      ? ["inventory-turnover-trend", ...periods.flatMap((period) => [period.key, period.startDate, period.endDate]), session.userId ?? "guest"]
      : null;

  return useSWR<ApiEnvelope<InventoryTurnoverTrendBucket[]>>(swrKey, async () => {
    const token = await session.getToken();
    const buckets = await Promise.all(
      periods.map(async (period) => {
        const response = await fetchInventoryTurnover(period.startDate, period.endDate, token);
        return {
          ...period,
          rows: response.data,
        } satisfies InventoryTurnoverTrendBucket;
      }),
    );

    return {
      data: buckets,
      meta: {
        cached: false,
        timestamp: new Date().toISOString(),
      },
    };
  });
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

export function usePipelineStatus(enabled = true) {
  return useAuthedQuery<PipelineStatus>(["pipeline-status", enabled], (token) => fetchPipelineStatus(token), enabled);
}
