import type {
  AnalyticsFilterOptions,
  ApiResponse,
  ForecastGenerateRequest,
  ForecastRecordResponse,
  InventoryHistoryItem,
  InventorySummaryItem,
  InventoryTurnoverItem,
  PipelineStatusItem,
  RegionalGrowthItem,
  SalesAnalyticsItem,
  SupplierReliabilityItem,
} from "@/types";

const API_BASE_URL =
  process.env.INTERNAL_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === "") {
      return;
    }
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

async function request<T>(path: string, init?: RequestInit, token?: string | null): Promise<ApiResponse<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const rawBody = await response.text();
    if (rawBody) {
      try {
        const body = JSON.parse(rawBody) as { detail?: string };
        if (body.detail) {
          throw new Error(body.detail);
        }
      } catch (error) {
        if (error instanceof Error && error.message !== rawBody) {
          throw error;
        }
        throw new Error(rawBody);
      }
    }
    throw new Error(`API request failed: ${response.status}`);
  }

  return (await response.json()) as ApiResponse<T>;
}

export function fetchInventorySummary(regionId?: string, token?: string | null): Promise<ApiResponse<InventorySummaryItem[]>> {
  return request<InventorySummaryItem[]>(`/inventory/summary${buildQuery({ region_id: regionId })}`, undefined, token);
}

export function fetchInventoryHistory(
  productId: string,
  token?: string | null,
): Promise<ApiResponse<InventoryHistoryItem[]>> {
  return request<InventoryHistoryItem[]>(`/inventory/${productId}/history`, undefined, token);
}

export function fetchLowStock(regionId?: string, token?: string | null): Promise<ApiResponse<InventorySummaryItem[]>> {
  return request<InventorySummaryItem[]>(`/inventory/low-stock${buildQuery({ region_id: regionId })}`, undefined, token);
}

export function fetchSalesAnalytics(
  params?: { startDate?: string; endDate?: string; regionId?: string },
  token?: string | null,
): Promise<ApiResponse<SalesAnalyticsItem[]>> {
  return request<SalesAnalyticsItem[]>(
    `/analytics/sales${buildQuery({
      start_date: params?.startDate,
      end_date: params?.endDate,
      region_id: params?.regionId,
    })}`,
    undefined,
    token,
  );
}

export function fetchAnalyticsFilterOptions(token?: string | null): Promise<ApiResponse<AnalyticsFilterOptions>> {
  return request<AnalyticsFilterOptions>("/analytics/filter-options", undefined, token);
}

export function fetchInventoryTurnover(
  params?: { startDate?: string; endDate?: string },
  token?: string | null,
): Promise<ApiResponse<InventoryTurnoverItem[]>> {
  return request<InventoryTurnoverItem[]>(
    `/analytics/turnover${buildQuery({
      start_date: params?.startDate,
      end_date: params?.endDate,
    })}`,
    undefined,
    token,
  );
}

export function fetchSupplierReliability(token?: string | null): Promise<ApiResponse<SupplierReliabilityItem[]>> {
  return request<SupplierReliabilityItem[]>("/analytics/supplier-reliability", undefined, token);
}

export function fetchRegionalGrowth(token?: string | null): Promise<ApiResponse<RegionalGrowthItem[]>> {
  return request<RegionalGrowthItem[]>("/analytics/regional-growth", undefined, token);
}

export function generateForecast(
  payload: ForecastGenerateRequest,
  token?: string | null,
): Promise<ApiResponse<ForecastRecordResponse>> {
  return request<ForecastRecordResponse>(
    "/forecast/generate",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function fetchLatestForecast(
  productId: string,
  regionId: string,
  token?: string | null,
): Promise<ApiResponse<ForecastRecordResponse>> {
  return request<ForecastRecordResponse>(`/forecast/latest/${productId}/${regionId}`, undefined, token);
}

export function fetchForecastHistory(
  productId: string,
  token?: string | null,
): Promise<ApiResponse<ForecastRecordResponse[]>> {
  return request<ForecastRecordResponse[]>(`/forecast/history/${productId}`, undefined, token);
}

export function fetchPipelineStatus(token?: string | null): Promise<ApiResponse<PipelineStatusItem>> {
  return request<PipelineStatusItem>("/pipeline/status", undefined, token);
}
