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
async function request<T>(path: string, init?: RequestInit, token?: string | null): Promise<T> {
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
    const message = await response.text();
    throw new Error(message || `API request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function fetchAnalyticsOverview(regionCode?: string, token?: string | null): Promise<AnalyticsOverviewResponse> {
  return request<AnalyticsOverviewResponse>(`/analytics/overview${buildQuery({ region_id: regionCode })}`, undefined, token);
}

export function fetchSupplierPerformance(regionCode?: string, token?: string | null): Promise<SupplierPerformanceResponse> {
  return request<SupplierPerformanceResponse>(`/analytics/supplier-performance${buildQuery({ region_id: regionCode })}`, undefined, token);
}

export function fetchAlerts(regionCode?: string, token?: string | null): Promise<AlertListResponse> {
  return request<AlertListResponse>(`/analytics/alerts${buildQuery({ region_id: regionCode })}`, undefined, token);
}

export function fetchInventoryPositions(
  regionCode?: string,
  belowReorderOnly = false,
  token?: string | null,
): Promise<InventoryPositionResponse> {
  return request<InventoryPositionResponse>(
    `/inventory/positions${buildQuery({ region_id: regionCode, below_reorder_only: belowReorderOnly })}`,
    undefined,
    token,
  );
}

export function fetchStockouts(regionCode?: string, token?: string | null): Promise<InventoryPositionResponse> {
  return request<InventoryPositionResponse>(
    `/inventory/stockouts${buildQuery({ region_id: regionCode, below_reorder_only: true })}`,
    undefined,
    token,
  );
}

export function generateForecast(payload: ForecastGenerateRequest, token?: string | null): Promise<ForecastRecordResponse> {
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
): Promise<ForecastRecordResponse> {
  return request<ForecastRecordResponse>(`/forecast/latest/${productId}/${regionId}`, undefined, token);
}

export function fetchForecastHistory(productId: string, token?: string | null): Promise<ForecastHistoryResponse> {
  return request<ForecastHistoryResponse>(`/forecast/history/${productId}`, undefined, token);
}

export function rebalanceInventory(
  payload: InventoryRebalanceRequest,
  token?: string | null,
): Promise<InventoryRebalanceResponse> {
  return request<InventoryRebalanceResponse>(
    "/inventory/rebalance",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}
