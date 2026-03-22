"""Pydantic request and response models for SupplyIQ."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SeverityLevel = Literal["low", "medium", "high", "critical"]


class ApiError(BaseModel):
    """Represents a structured API error."""

    detail: str
    error_code: str


class AnalyticsQuery(BaseModel):
    """Validates analytics overview requests."""

    region_code: str | None = Field(default=None, min_length=2, max_length=32)
    lookback_days: int = Field(default=30, ge=7, le=365)


class AlertQuery(BaseModel):
    """Validates alert listing requests."""

    region_code: str | None = Field(default=None, min_length=2, max_length=32)
    severity: SeverityLevel | None = None
    limit: int = Field(default=6, ge=1, le=50)


class InventoryQuery(BaseModel):
    """Validates inventory listing requests."""

    region_code: str | None = Field(default=None, min_length=2, max_length=32)
    below_reorder_only: bool = False
    limit: int = Field(default=25, ge=1, le=100)


class ForecastGenerateRequest(BaseModel):
    """Validates forecast generation requests."""

    product_id: UUID
    region_id: UUID
    horizon_days: int = Field(default=30, ge=1, le=90)


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
    region_code: str | None
    kpis: list[KPI]
    demand_series: list[DemandPoint]


class SupplierPerformanceItem(BaseModel):
    """Represents supplier performance metrics."""

    supplier_id: UUID
    supplier_code: str
    name: str
    reliability_score: float
    lead_time_days: int
    active_products: int
    fill_rate_pct: float
    risk_level: SeverityLevel


class SupplierPerformanceResponse(BaseModel):
    """Represents the supplier analytics payload."""

    generated_at: datetime
    items: list[SupplierPerformanceItem]


class AlertItem(BaseModel):
    """Represents an active inventory alert."""

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
    quantity_on_hand: int
    quantity_reserved: int
    inbound_units: int
    reorder_point: int
    days_of_cover: float
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


class ForecastRecordResponse(BaseModel):
    """Represents a forecast result."""

    model_config = ConfigDict(from_attributes=True)

    forecast_id: UUID
    product_id: UUID
    region_id: UUID
    product_name: str
    region_name: str
    horizon_days: int
    predicted_demand_units: int
    lower_bound_units: int
    upper_bound_units: int
    stockout_probability_pct: float
    recommended_reorder_units: int
    model_version: str
    generated_at: datetime


class ForecastHistoryResponse(BaseModel):
    """Represents forecast history for a product."""

    generated_at: datetime
    items: list[ForecastRecordResponse]
