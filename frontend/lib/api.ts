import type {
  AlertListResponse,
  AnalyticsOverviewResponse,
  ForecastGenerateRequest,
  ForecastHistoryResponse,
  ForecastRecordResponse,
  InventoryPositionResponse,
  InventoryRebalanceRequest,
  InventoryRebalanceResponse,
  SupplierPerformanceResponse,
} from "@/types";

const API_BASE_URL =
  process.env.INTERNAL_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";

/** Builds a query string while keeping undefined values out of the request. */
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

/** Sends a typed HTTP request to the backend API. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function fetchAnalyticsOverview(regionCode?: string): Promise<AnalyticsOverviewResponse> {
  return request<AnalyticsOverviewResponse>(`/analytics/overview${buildQuery({ region_code: regionCode })}`);
}

export function fetchSupplierPerformance(regionCode?: string): Promise<SupplierPerformanceResponse> {
  return request<SupplierPerformanceResponse>(`/analytics/supplier-performance${buildQuery({ region_code: regionCode })}`);
}

export function fetchAlerts(regionCode?: string): Promise<AlertListResponse> {
  return request<AlertListResponse>(`/analytics/alerts${buildQuery({ region_code: regionCode })}`);
}

export function fetchInventoryPositions(regionCode?: string, belowReorderOnly = false): Promise<InventoryPositionResponse> {
  return request<InventoryPositionResponse>(
    `/inventory/positions${buildQuery({ region_code: regionCode, below_reorder_only: belowReorderOnly })}`,
  );
}

export function fetchStockouts(regionCode?: string): Promise<InventoryPositionResponse> {
  return request<InventoryPositionResponse>(`/inventory/stockouts${buildQuery({ region_code: regionCode, below_reorder_only: true })}`);
}

export function generateForecast(payload: ForecastGenerateRequest): Promise<ForecastRecordResponse> {
  return request<ForecastRecordResponse>("/forecast/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchLatestForecast(productId: string, regionId: string): Promise<ForecastRecordResponse> {
  return request<ForecastRecordResponse>(`/forecast/latest/${productId}/${regionId}`);
}

export function fetchForecastHistory(productId: string): Promise<ForecastHistoryResponse> {
  return request<ForecastHistoryResponse>(`/forecast/history/${productId}`);
}

export function rebalanceInventory(payload: InventoryRebalanceRequest): Promise<InventoryRebalanceResponse> {
  return request<InventoryRebalanceResponse>("/inventory/rebalance", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
