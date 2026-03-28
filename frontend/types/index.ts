export type UserRole = "admin" | "analyst" | "viewer";
export type SeverityLevel = "low" | "medium" | "high" | "critical";

export interface ApiMeta {
  timestamp: string;
  cached: boolean;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: ApiMeta;
}

export interface SessionSnapshot {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  displayName: string;
  primaryEmail: string | null;
  role: UserRole;
  roleLabel: string;
  canViewForecast: boolean;
  canGenerateForecast: boolean;
  canViewPipeline: boolean;
  getToken: () => Promise<string | null>;
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

export interface InventoryHistoryItem {
  product_id: string;
  product_name: string;
  region_id: string;
  region_name: string;
  snapshot_date: string;
  quantity: number;
}

export interface SalesAnalyticsItem {
  region_id: string;
  region_name: string;
  sale_date: string;
  units_sold: number;
  revenue: number;
}

export interface ProductSalesSummaryItem {
  product_id: string;
  product_name: string;
  sku: string;
  category: string | null;
  units_sold: number;
  revenue: number;
}

export interface InventoryTurnoverItem {
  product_id: string;
  product_name: string;
  sku: string;
  cost_of_goods: number;
  average_inventory_value: number;
  turnover_ratio: number;
}

export interface InventoryTurnoverTrendPeriod {
  key: string;
  label: string;
  startDate: string;
  endDate: string;
}

export interface InventoryTurnoverTrendBucket extends InventoryTurnoverTrendPeriod {
  rows: InventoryTurnoverItem[];
}

export interface SupplierPerformanceItem {
  supplier_name: string;
  shipment_count: number;
  delivered_count: number;
  delayed_count: number;
  in_transit_count: number;
  on_time_rate_pct: number;
}

export interface RegionalGrowthItem {
  region_id: string;
  region_name: string;
  current_month: string;
  previous_month: string | null;
  revenue: number;
  previous_revenue: number;
  growth_pct: number;
}

export interface AnalyticsFilterRegion {
  region_id: string;
  region_name: string;
}

export interface AnalyticsFilterProduct {
  product_id: string;
  product_name: string;
  sku: string;
  category: string | null;
}

export interface AnalyticsFilterOptions {
  regions: AnalyticsFilterRegion[];
  products: AnalyticsFilterProduct[];
  categories: string[];
}

export interface ForecastRunCount {
  count: number;
}

export interface DemandPoint {
  label: string;
  demand_units: number;
}

export interface ForecastGenerateRequest {
  product_id: string;
  region_id: string;
}

export interface ForecastPredictionPoint {
  date: string;
  predicted_units?: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
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

export interface ForecastPayload {
  horizon_days: number;
  predictions: ForecastPredictionPoint[];
  summary: ForecastSummary;
}

export interface ForecastFeatureContribution {
  feature: string;
  contribution: number;
  value?: number | null;
  direction?: "up" | "down" | null;
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

export interface PipelineStatus {
  flow_run_id: string | null;
  flow_name: string | null;
  deployment_id: string | null;
  deployment_name: string | null;
  state_type: string | null;
  state_name: string | null;
  start_time: string | null;
  end_time: string | null;
  next_scheduled_run_time: string | null;
}
