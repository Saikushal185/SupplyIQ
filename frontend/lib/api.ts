import type {
  AnalyticsFilterOptions,
  ApiEnvelope,
  ForecastGenerateRequest,
  ForecastRecordResponse,
  ForecastRunCount,
  InventoryPositionItem,
  InventoryTurnoverItem,
  PipelineStatus,
  ProductSalesSummaryItem,
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
async function request<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as ApiEnvelope<T>;
}

async function requestAllow404<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T> | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
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

export function fetchInventorySummary(regionId?: string) {
  return request<InventoryPositionItem[]>(`/inventory/summary${buildQuery({ region_id: regionId })}`);
}

export function fetchLowStock(regionId?: string) {
  return request<InventoryPositionItem[]>(`/inventory/low-stock${buildQuery({ region_id: regionId })}`);
}

export function fetchSalesAnalytics(startDate?: string, endDate?: string, regionId?: string) {
  return request<SalesAnalyticsItem[]>(
    `/analytics/sales${buildQuery({
      start_date: startDate,
      end_date: endDate,
      region_id: regionId,
    })}`,
  );
}

export function fetchAnalyticsFilters() {
  return request<AnalyticsFilterOptions>("/analytics/filters");
}

export function fetchProductSales(startDate?: string, endDate?: string, regionId?: string, category?: string) {
  return request<ProductSalesSummaryItem[]>(
    `/analytics/product-sales${buildQuery({
      start_date: startDate,
      end_date: endDate,
      region_id: regionId,
      category,
    })}`,
  );
}

export function fetchForecastRunCount(runDate?: string) {
  return request<ForecastRunCount>(`/analytics/forecast-runs${buildQuery({ run_date: runDate })}`);
}

export function fetchInventoryTurnover(startDate?: string, endDate?: string) {
  return request<InventoryTurnoverItem[]>(
    `/analytics/turnover${buildQuery({
      start_date: startDate,
      end_date: endDate,
    })}`,
  );
}

export function fetchSupplierReliability(regionId?: string) {
  return request<SupplierPerformanceItem[]>(`/analytics/supplier-reliability${buildQuery({ region_id: regionId })}`);
}

export function fetchRegionalGrowth() {
  return request<RegionalGrowthItem[]>("/analytics/regional-growth");
}

export function generateForecast(payload: ForecastGenerateRequest) {
  return request<ForecastRecordResponse>("/forecast/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchLatestForecast(productId: string, regionId: string) {
  return requestAllow404<ForecastRecordResponse>(`/forecast/latest/${productId}/${regionId}`);
}

export function fetchForecastHistory(productId: string) {
  return request<ForecastRecordResponse[]>(`/forecast/history/${productId}`);
}

export function fetchPipelineStatus() {
  return request<PipelineStatus>("/pipeline/status");
}
