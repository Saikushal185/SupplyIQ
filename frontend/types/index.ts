export type SeverityLevel = "low" | "medium" | "high" | "critical";

export interface KPI {
  label: string;
  value: number;
  unit: string;
  change_note: string;
}

export interface DemandPoint {
  label: string;
  demand_units: number;
}

export interface AnalyticsOverviewResponse {
  generated_at: string;
  region_code: string | null;
  kpis: KPI[];
  demand_series: DemandPoint[];
}

export interface SupplierPerformanceItem {
  supplier_id: string;
  supplier_code: string;
  name: string;
  reliability_score: number;
  lead_time_days: number;
  active_products: number;
  fill_rate_pct: number;
  risk_level: SeverityLevel;
}

export interface SupplierPerformanceResponse {
  generated_at: string;
  items: SupplierPerformanceItem[];
}

export interface AlertItem {
  alert_id: string;
  product_id: string;
  region_id: string;
  product_name: string;
  region_name: string;
  severity: SeverityLevel;
  message: string;
  triggered_by: string;
  created_at: string;
}

export interface AlertListResponse {
  generated_at: string;
  items: AlertItem[];
}

export interface InventoryPositionItem {
  product_id: string;
  product_name: string;
  sku: string;
  region_id: string;
  region_name: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  inbound_units: number;
  reorder_point: number;
  days_of_cover: number;
  risk_level: SeverityLevel;
}

export interface InventoryPositionResponse {
  generated_at: string;
  items: InventoryPositionItem[];
}

export interface ForecastGenerateRequest {
  product_id: string;
  region_id: string;
  horizon_days: number;
}

export interface ForecastRecordResponse {
  forecast_id: string;
  product_id: string;
  region_id: string;
  product_name: string;
  region_name: string;
  horizon_days: number;
  predicted_demand_units: number;
  lower_bound_units: number;
  upper_bound_units: number;
  stockout_probability_pct: number;
  recommended_reorder_units: number;
  model_version: string;
  generated_at: string;
}

export interface ForecastHistoryResponse {
  generated_at: string;
  items: ForecastRecordResponse[];
}

export interface InventoryRebalanceRequest {
  source_region_id: string;
  target_region_id: string;
  product_id: string;
  quantity_units: number;
}

export interface InventoryRebalanceResponse {
  generated_at: string;
  product_id: string;
  source_region_id: string;
  target_region_id: string;
  quantity_units: number;
  status: string;
}
