"""Pydantic request and response models for SupplyIQ."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SeverityLevel = Literal["low", "medium", "high", "critical"]
UserRole = Literal["admin", "analyst", "viewer"]
PayloadT = TypeVar("PayloadT")


class ApiError(BaseModel):
    """Represents a structured API error."""

    detail: str
    error_code: str


class ResponseMeta(BaseModel):
    """Metadata included with every API response."""

    timestamp: datetime
    cached: bool


class ApiEnvelope(BaseModel, Generic[PayloadT]):
    """Standard API response envelope."""

    data: PayloadT
    meta: ResponseMeta


class AnalyticsQuery(BaseModel):
    """Validates analytics overview requests."""

    region_id: UUID | None = None
    lookback_days: int = Field(default=30, ge=7, le=365)


class DateRangeQuery(BaseModel):
    """Validates analytics date range filters."""

    start_date: date | None = None
    end_date: date | None = None
    region_id: UUID | None = None


class AlertQuery(BaseModel):
    """Validates alert listing requests."""

    region_id: UUID | None = None
    severity: SeverityLevel | None = None
    limit: int = Field(default=6, ge=1, le=50)


class InventoryQuery(BaseModel):
    """Validates inventory listing requests."""

    region_id: UUID | None = None
    below_reorder_only: bool = False
    limit: int = Field(default=25, ge=1, le=100)


class ForecastGenerateRequest(BaseModel):
    """Validates forecast generation requests."""

    product_id: UUID
    region_id: UUID


class ForecastPathRequest(BaseModel):
    """Validates product and region path parameters."""

    product_id: UUID
    region_id: UUID


class ProductPathRequest(BaseModel):
    """Validates product-only path parameters."""

    product_id: UUID


class InventoryRebalanceRequest(BaseModel):
    """Validates inventory transfer requests."""

    source_region_id: UUID
    target_region_id: UUID
    product_id: UUID
    quantity_units: int = Field(..., gt=0, le=100000)


class KPI(BaseModel):
    """Represents a dashboard KPI metric."""

    label: str
    value: float | int | Decimal
    unit: str = ""
    change_note: str


class DemandPoint(BaseModel):
    """Represents a point in a demand trend series."""

    label: str
    demand_units: int


class AnalyticsOverviewResponse(BaseModel):
    """Represents analytics overview data."""

    generated_at: datetime
    region_id: UUID | None
    kpis: list[KPI]
    demand_series: list[DemandPoint]


class SupplierPerformanceItem(BaseModel):
    """Represents supplier shipment performance metrics."""

    supplier_name: str
    shipment_count: int
    delivered_count: int
    delayed_count: int
    in_transit_count: int
    on_time_rate_pct: float


class SupplierPerformanceResponse(BaseModel):
    """Represents the supplier analytics payload."""

    generated_at: datetime
    items: list[SupplierPerformanceItem]


class AlertItem(BaseModel):
    """Represents a derived low-stock alert."""

    alert_id: UUID
    product_id: UUID
    region_id: UUID
    product_name: str
    region_name: str
    severity: SeverityLevel
    message: str
    triggered_by: str
    created_at: datetime


class AlertListResponse(BaseModel):
    """Represents the alert listing payload."""

    generated_at: datetime
    items: list[AlertItem]


class InventoryPositionItem(BaseModel):
    """Represents an inventory position row."""

    product_id: UUID
    product_name: str
    sku: str
    region_id: UUID
    region_name: str
    quantity: int
    snapshot_date: date
    reorder_point: int | None
    risk_level: SeverityLevel


class InventoryPositionResponse(BaseModel):
    """Represents the inventory positions payload."""

    generated_at: datetime
    items: list[InventoryPositionItem]


class InventoryRebalanceResponse(BaseModel):
    """Represents a completed rebalance operation."""

    generated_at: datetime
    product_id: UUID
    source_region_id: UUID
    target_region_id: UUID
    quantity_units: int
    status: str


class ForecastPredictionPoint(BaseModel):
    """Represents a single forecasted day."""

    date: date
    predicted_units: int | None = None
    lower_bound: int | None = None
    upper_bound: int | None = None
    units: int
    lower: int
    upper: int


class ForecastSummary(BaseModel):
    """Represents forecast summary metrics."""

    total_units: int
    avg_daily_units: float
    stockout_risk_pct: float
    recommended_reorder_units: int


class ForecastPayload(BaseModel):
    """Represents the persisted forecast JSON payload."""

    horizon_days: int
    predictions: list[ForecastPredictionPoint]
    summary: ForecastSummary


class ForecastFeatureContribution(BaseModel):
    """Represents a top feature contribution entry."""

    feature: str
    contribution: float
    value: float | None = None
    direction: Literal["up", "down"] | None = None


class ForecastExplainabilityPayload(BaseModel):
    """Represents the persisted explanation payload."""

    method: str
    top_features: list[ForecastFeatureContribution]


class ForecastRecordResponse(BaseModel):
    """Represents a forecast result."""

    model_config = ConfigDict(from_attributes=True)

    forecast_id: UUID
    product_id: UUID
    region_id: UUID
    product_name: str
    region_name: str
    run_at: datetime
    forecast_json: ForecastPayload
    shap_json: ForecastExplainabilityPayload


class ForecastHistoryResponse(BaseModel):
    """Represents forecast history for a product."""

    generated_at: datetime
    items: list[ForecastRecordResponse]


class InventoryHistoryItem(BaseModel):
    """Represents a historical inventory snapshot row."""

    region_id: UUID
    region_name: str
    snapshot_date: date
    quantity: int


class SalesAnalyticsItem(BaseModel):
    """Represents daily sales aggregated by region."""

    region_id: UUID
    region_name: str
    sale_date: date
    units_sold: int
    revenue: float


class InventoryTurnoverItem(BaseModel):
    """Represents product-level inventory turnover analytics."""

    product_id: UUID
    product_name: str
    sku: str
    cost_of_goods: float
    average_inventory_value: float
    turnover_ratio: float


class SupplierReliabilityItem(BaseModel):
    """Represents on-time delivery performance by supplier."""

    supplier_name: str
    shipment_count: int
    delivered_count: int
    on_time_deliveries: int
    on_time_rate_pct: float


class RegionalGrowthItem(BaseModel):
    """Represents the latest month-over-month revenue growth for a region."""

    region_id: UUID
    region_name: str
    current_month: date
    previous_month: date | None = None
    revenue: float
    previous_revenue: float
    growth_pct: float


class PipelineStatusItem(BaseModel):
    """Represents the latest Prefect flow run status."""

    flow_run_id: str | None = None
    flow_name: str | None = None
    deployment_id: str | None = None
    deployment_name: str | None = None
    state_type: str | None = None
    state_name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    next_scheduled_run_time: datetime | None = None
