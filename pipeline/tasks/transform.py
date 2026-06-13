"""Transformation tasks for SupplyIQ pipeline."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
    PYDANTIC_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - exercised only in lightweight local test environments
    BaseModel = object  # type: ignore[assignment]
    ConfigDict = dict  # type: ignore[assignment]
    Field = lambda *args, **kwargs: None  # type: ignore[assignment]
    ValidationError = ValueError  # type: ignore[assignment]
    PYDANTIC_AVAILABLE = False

    def field_validator(*_args, **_kwargs):  # type: ignore[misc]
        def decorator(func):
            return func
        return decorator

class ExtractedSaleRow(BaseModel):
    """Validates extracted daily sales before loading."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_id: Any
    region_id: Any
    sale_date: Any
    units_sold: int = Field(ge=0)
    weather_temp: float | None = None
    traffic_index: float | None = None

    @field_validator("product_id", "region_id")
    @classmethod
    def require_identifier(cls, value: object) -> object:
        """Rejects missing product and region identifiers."""

        if value is None:
            raise ValueError("product and region ids are required")
        return value

    @classmethod
    def validate_row(cls, row: dict[str, object]) -> "ExtractedSaleRow":
        """Validates a sale row even when pydantic is not installed locally."""

        if PYDANTIC_AVAILABLE:
            return cls.model_validate(row)  # type: ignore[return-value]
        if row.get("product_id") is None or row.get("region_id") is None:
            raise ValidationError("product and region ids are required")
        units_sold = int(row.get("units_sold") or 0)
        if units_sold < 0:
            raise ValidationError("units_sold must be greater than or equal to 0")
        instance = cls()
        instance.product_id = row.get("product_id")
        instance.region_id = row.get("region_id")
        instance.sale_date = row.get("sale_date")
        instance.units_sold = units_sold
        instance.weather_temp = float(row["weather_temp"]) if row.get("weather_temp") is not None else None
        instance.traffic_index = float(row["traffic_index"]) if row.get("traffic_index") is not None else None
        return instance


class ExtractedInventoryRow(BaseModel):
    """Validates the inventory input rows used for load projections."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_id: Any
    region_id: Any
    snapshot_date: Any
    opening_quantity: int = Field(ge=0)

    @field_validator("product_id", "region_id")
    @classmethod
    def require_identifier(cls, value: object) -> object:
        """Rejects missing product and region identifiers."""

        if value is None:
            raise ValueError("product and region ids are required")
        return value

    @classmethod
    def validate_row(cls, row: dict[str, object]) -> "ExtractedInventoryRow":
        """Validates an inventory row even when pydantic is not installed locally."""

        if PYDANTIC_AVAILABLE:
            return cls.model_validate(row)  # type: ignore[return-value]
        if row.get("product_id") is None or row.get("region_id") is None:
            raise ValidationError("product and region ids are required")
        opening_quantity = int(row.get("opening_quantity") or 0)
        if opening_quantity < 0:
            raise ValidationError("opening_quantity must be greater than or equal to 0")
        instance = cls()
        instance.product_id = row.get("product_id")
        instance.region_id = row.get("region_id")
        instance.snapshot_date = row.get("snapshot_date")
        instance.opening_quantity = opening_quantity
        return instance


def transform_supply_data(raw_data: dict[str, list[dict[str, object]]]) -> dict[str, list[dict[str, object]]]:
    """Validates, enriches, and flags the extracted supply data."""

    product_lookup = {
        str(row["product_id"]): row
        for row in raw_data.get("products", [])
        if row.get("product_id") is not None
    }
    valid_sales: list[dict[str, object]] = []
    rejected_daily_sales: list[dict[str, object]] = []
    units_by_scope: dict[tuple[str, str], int] = defaultdict(int)

    for sale_row in raw_data.get("daily_sales", []):
        try:
            validated = ExtractedSaleRow.validate_row(sale_row)
        except ValidationError as exc:
            rejected_daily_sales.append(
                {
                    "row": sale_row,
                    "errors": exc.errors() if hasattr(exc, "errors") else [{"msg": str(exc)}],
                }
            )
            continue

        product = product_lookup.get(str(validated.product_id))
        if product is None:
            rejected_daily_sales.append(
                {
                    "row": sale_row,
                    "errors": [{"msg": "product_id does not exist in products payload"}],
                }
            )
            continue

        revenue = round(validated.units_sold * float(product.get("unit_cost") or 0), 2)
        enriched_row = {
            "product_id": validated.product_id,
            "region_id": validated.region_id,
            "sale_date": validated.sale_date,
            "units_sold": validated.units_sold,
            "weather_temp": validated.weather_temp,
            "traffic_index": validated.traffic_index,
            "revenue": revenue,
        }
        valid_sales.append(enriched_row)
        units_by_scope[(str(validated.product_id), str(validated.region_id))] += validated.units_sold

    transformed_inventory: list[dict[str, object]] = []
    for inventory_row in raw_data.get("inventory_snapshots", []):
        validated_inventory = ExtractedInventoryRow.validate_row(inventory_row)
        product = product_lookup.get(str(validated_inventory.product_id))
        reorder_point = int(product.get("reorder_point") or 0) if product is not None else 0
        units_sold = units_by_scope[(str(validated_inventory.product_id), str(validated_inventory.region_id))]
        projected_quantity = max(validated_inventory.opening_quantity - units_sold, 0)
        transformed_inventory.append(
            {
                "product_id": validated_inventory.product_id,
                "region_id": validated_inventory.region_id,
                "snapshot_date": validated_inventory.snapshot_date,
                "opening_quantity": validated_inventory.opening_quantity,
                "units_sold": units_sold,
                "projected_quantity": projected_quantity,
                "below_reorder": projected_quantity < reorder_point if reorder_point > 0 else False,
            }
        )

    return {
        "products": list(raw_data.get("products", [])),
        "regions": list(raw_data.get("regions", [])),
        "daily_sales": valid_sales,
        "inventory_snapshots": transformed_inventory,
        "rejected_daily_sales": rejected_daily_sales,
    }
