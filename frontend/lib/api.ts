import type {
  ApiEnvelope,
  ForecastGenerateRequest,
  ForecastRecordResponse,
  InventoryHistoryItem,
  InventoryPositionItem,
  InventoryTurnoverItem,
  PipelineStatus,
  RegionalGrowthItem,
  SalesAnalyticsItem,
  SupplierPerformanceItem,
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

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  }

  const message = await response.text();
  return message || `API request failed: ${response.status}`;
}

/** Sends a typed HTTP request to the backend API. */
async function request<T>(
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<ApiEnvelope<T>> {
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
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as ApiEnvelope<T>;
}

async function requestAllow404<T>(
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<ApiEnvelope<T> | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as ApiEnvelope<T>;
}

export function fetchInventorySummary(regionId?: string, token?: string | null) {
  return request<InventoryPositionItem[]>(`/inventory/summary${buildQuery({ region_id: regionId })}`, undefined, token);
}

export function fetchLowStock(regionId?: string, token?: string | null) {
  return request<InventoryPositionItem[]>(`/inventory/low-stock${buildQuery({ region_id: regionId })}`, undefined, token);
}

export function fetchInventoryHistory(productId: string, token?: string | null) {
  return request<InventoryHistoryItem[]>(`/inventory/${productId}/history`, undefined, token);
}

export function fetchSalesAnalytics(startDate?: string, endDate?: string, regionId?: string, token?: string | null) {
  return request<SalesAnalyticsItem[]>(
    `/analytics/sales${buildQuery({
      start_date: startDate,
      end_date: endDate,
      region_id: regionId,
    })}`,
    undefined,
    token,
  );
}

export function fetchInventoryTurnover(startDate?: string, endDate?: string, token?: string | null) {
  return request<InventoryTurnoverItem[]>(
    `/analytics/turnover${buildQuery({
      start_date: startDate,
      end_date: endDate,
    })}`,
    undefined,
    token,
  );
}

export function fetchSupplierReliability(regionId?: string, token?: string | null) {
  return request<SupplierPerformanceItem[]>(
    `/analytics/supplier-reliability${buildQuery({ region_id: regionId })}`,
    undefined,
    token,
  );
}

export function fetchRegionalGrowth(token?: string | null) {
  return request<RegionalGrowthItem[]>("/analytics/regional-growth", undefined, token);
}

export function generateForecast(payload: ForecastGenerateRequest, token?: string | null) {
  return request<ForecastRecordResponse>(
    "/forecast/generate",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function fetchLatestForecast(productId: string, regionId: string, token?: string | null) {
  return requestAllow404<ForecastRecordResponse>(`/forecast/latest/${productId}/${regionId}`, undefined, token);
}

export function fetchForecastHistory(productId: string, token?: string | null) {
  return request<ForecastRecordResponse[]>(`/forecast/history/${productId}`, undefined, token);
}

export function fetchPipelineStatus(token?: string | null) {
  return request<PipelineStatus>("/pipeline/status", undefined, token);
}
