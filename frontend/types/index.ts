export type SeverityLevel = "low" | "medium" | "high" | "critical";

export interface SessionSnapshot {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  displayName: string;
  primaryEmail: string | null;
  roleLabel: string;
  getToken: () => Promise<string | null>;
}

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
  region_id: string | null;
  kpis: KPI[];
  demand_series: DemandPoint[];
}

export interface SupplierPerformanceItem {
  supplier_name: string;
  shipment_count: number;
  delivered_count: number;
  delayed_count: number;
  in_transit_count: number;
  on_time_rate_pct: number;
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
  quantity: number;
  snapshot_date: string;
  reorder_point: number | null;
  risk_level: SeverityLevel;
}

export interface InventoryPositionResponse {
  generated_at: string;
  items: InventoryPositionItem[];
}

export interface ForecastGenerateRequest {
  product_id: string;
  region_id: string;
}

export interface ForecastPredictionPoint {
  date: string;
  units: number;
  lower: number;
  upper: number;
}

export interface ForecastSummary {
  total_units: number;
  avg_daily_units: number;
  stockout_risk_pct: number;
  recommended_reorder_units: number;
}

export interface ForecastFeatureContribution {
  feature: string;
  contribution: number;
}

export interface ForecastPayload {
  horizon_days: number;
  predictions: ForecastPredictionPoint[];
  summary: ForecastSummary;
}

export interface ForecastExplainabilityPayload {
  method: string;
  top_features: ForecastFeatureContribution[];
}

export interface ForecastRecordResponse {
  forecast_id: string;
  product_id: string;
  region_id: string;
  product_name: string;
  region_name: string;
  run_at: string;
  forecast_json: ForecastPayload;
  shap_json: ForecastExplainabilityPayload;
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
