"use client";

import useSWR from "swr";

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

function useQuery<T>(key: SwrKey, fetcher: () => Promise<ApiEnvelope<T>>, enabled = true) {
  return useSWR<ApiEnvelope<T>>(enabled ? key : null, fetcher);
}

function useOptionalQuery<T>(key: SwrKey, fetcher: () => Promise<ApiEnvelope<T> | null>, enabled = true) {
  return useSWR<ApiEnvelope<T> | null>(enabled ? key : null, fetcher);
}

export function useInventorySummary(regionId?: string) {
  return useQuery<InventoryPositionItem[]>(["inventory-summary", regionId], () => fetchInventorySummary(regionId));
}

export function useLowStock(regionId?: string) {
  return useQuery<InventoryPositionItem[]>(["low-stock", regionId], () => fetchLowStock(regionId));
}

export function useSalesAnalytics(startDate?: string, endDate?: string, regionId?: string) {
  return useQuery<SalesAnalyticsItem[]>(["sales-analytics", startDate, endDate, regionId], () =>
    fetchSalesAnalytics(startDate, endDate, regionId),
  );
}

export function useAnalyticsFilters() {
  return useQuery<AnalyticsFilterOptions>(["analytics-filters"], () => fetchAnalyticsFilters());
}

export function useProductSales(startDate?: string, endDate?: string, regionId?: string, category?: string) {
  return useQuery<ProductSalesSummaryItem[]>(["product-sales", startDate, endDate, regionId, category], () =>
    fetchProductSales(startDate, endDate, regionId, category),
  );
}

export function useForecastRunCount(runDate?: string) {
  return useQuery<ForecastRunCount>(["forecast-run-count", runDate], () => fetchForecastRunCount(runDate));
}

export function useInventoryTurnover(startDate?: string, endDate?: string) {
  return useQuery<InventoryTurnoverItem[]>(["inventory-turnover", startDate, endDate], () =>
    fetchInventoryTurnover(startDate, endDate),
  );
}

export function useInventoryTurnoverTrend(periods: InventoryTurnoverTrendPeriod[]) {
  const swrKey = periods.length
    ? ["inventory-turnover-trend", ...periods.flatMap((period) => [period.key, period.startDate, period.endDate])]
    : null;

  return useSWR<ApiEnvelope<InventoryTurnoverTrendBucket[]>>(swrKey, async () => {
    const buckets = await Promise.all(
      periods.map(async (period) => {
        const response = await fetchInventoryTurnover(period.startDate, period.endDate);
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
  return useQuery<SupplierPerformanceItem[]>(["supplier-reliability", regionId], () =>
    fetchSupplierReliability(regionId),
  );
}

export function useRegionalGrowth() {
  return useQuery<RegionalGrowthItem[]>(["regional-growth"], () => fetchRegionalGrowth());
}

export function useLatestForecast(productId: string | null, regionId: string | null) {
  const shouldFetch = Boolean(productId && regionId);
  return useOptionalQuery<ForecastRecordResponse>(["latest-forecast", productId, regionId], async () => {
    if (!productId || !regionId) {
      return null;
    }
    return fetchLatestForecast(productId, regionId);
  }, shouldFetch);
}

export function useForecastHistory(productId: string | null) {
  const shouldFetch = Boolean(productId);
  return useOptionalQuery<ForecastRecordResponse[]>(["forecast-history", productId], async () => {
    if (!productId) {
      return null;
    }
    return fetchForecastHistory(productId);
  }, shouldFetch);
}

export function usePipelineStatus(enabled = true) {
  return useQuery<PipelineStatus>(["pipeline-status"], () => fetchPipelineStatus(), enabled);
}
