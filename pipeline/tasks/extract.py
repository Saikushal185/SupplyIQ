"""Extraction tasks for SupplyIQ pipeline."""

from __future__ import annotations

import math
from datetime import date, timedelta

try:
    from prefect import task
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def task(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator


REGIONS = [
    {"name": "Dallas Distribution Center", "country": "United States", "timezone": "America/Chicago"},
    {"name": "Chicago Cross-Dock", "country": "United States", "timezone": "America/Chicago"},
    {"name": "Los Angeles Fulfillment Hub", "country": "United States", "timezone": "America/Los_Angeles"},
]

PRODUCTS = [
    {"sku": "SKU-1001", "name": "Wireless Scanner", "category": "Electronics", "unit_cost": 82.0, "reorder_point": 640},
    {"sku": "SKU-1002", "name": "Smart Label Printer", "category": "Electronics", "unit_cost": 190.0, "reorder_point": 420},
    {"sku": "SKU-1003", "name": "Modular Shelf Bin", "category": "Storage", "unit_cost": 24.0, "reorder_point": 760},
    {"sku": "SKU-1004", "name": "Cold Chain Sensor", "category": "Monitoring", "unit_cost": 68.0, "reorder_point": 390},
    {"sku": "SKU-1005", "name": "Packing Tape Roll", "category": "Packaging", "unit_cost": 6.4, "reorder_point": 1500},
]

PRODUCT_REGION_PROFILES = [
    {"sku": "SKU-1001", "region_name": "Dallas Distribution Center", "base_units": 58, "seasonality": 9.5, "weather_base": 74.0, "traffic_base": 0.46},
    {"sku": "SKU-1002", "region_name": "Dallas Distribution Center", "base_units": 34, "seasonality": 6.0, "weather_base": 76.0, "traffic_base": 0.51},
    {"sku": "SKU-1003", "region_name": "Chicago Cross-Dock", "base_units": 87, "seasonality": 11.0, "weather_base": 51.0, "traffic_base": 0.38},
    {"sku": "SKU-1004", "region_name": "Los Angeles Fulfillment Hub", "base_units": 42, "seasonality": 5.0, "weather_base": 69.0, "traffic_base": 0.58},
    {"sku": "SKU-1005", "region_name": "Los Angeles Fulfillment Hub", "base_units": 124, "seasonality": 14.0, "weather_base": 71.0, "traffic_base": 0.66},
]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Constrains a value to the provided numeric range."""

    return max(minimum, min(value, maximum))


def _build_daily_sales(end_date: date) -> list[dict[str, object]]:
    """Builds a deterministic two-year sales history for every active product-region scope."""

    product_cost_lookup = {product["sku"]: float(product["unit_cost"]) for product in PRODUCTS}
    sales_rows: list[dict[str, object]] = []
    start_date = end_date - timedelta(days=729)

    for day_offset in range(730):
        sale_date = start_date + timedelta(days=day_offset)
        weekday = sale_date.weekday()
        yearly_wave = math.sin((day_offset / 365.0) * 2 * math.pi)
        monthly_wave = math.sin((day_offset / 30.0) * 2 * math.pi)

        for profile_index, profile in enumerate(PRODUCT_REGION_PROFILES):
            weekly_multiplier = 0.93 if weekday >= 5 else 1.05
            traffic_index = _clamp(
                profile["traffic_base"]
                + 0.06 * yearly_wave
                + 0.03 * monthly_wave
                + (0.03 if weekday < 5 else -0.015),
                0.18,
                0.95,
            )
            weather_temp = round(
                profile["weather_base"]
                + (10.0 * yearly_wave)
                + (2.5 * math.sin((day_offset / 14.0) + profile_index)),
                2,
            )
            units_sold = max(
                int(
                    round(
                        (
                            profile["base_units"]
                            + profile["seasonality"] * yearly_wave
                            + (traffic_index * 18)
                            + (2.5 * monthly_wave)
                        )
                        * weekly_multiplier
                    )
                ),
                6,
            )
            sales_rows.append(
                {
                    "sku": profile["sku"],
                    "region_name": profile["region_name"],
                    "sale_date": sale_date,
                    "units_sold": units_sold,
                    "revenue": round(units_sold * product_cost_lookup[profile["sku"]], 2),
                    "weather_temp": weather_temp,
                    "traffic_index": round(traffic_index, 2),
                }
            )

    return sales_rows


def _build_inventory_snapshots(snapshot_date: date) -> list[dict[str, object]]:
    """Builds the latest inventory picture used by the frontend and alerts."""

    return [
        {"sku": "SKU-1001", "region_name": "Dallas Distribution Center", "quantity": 920, "snapshot_date": snapshot_date},
        {"sku": "SKU-1002", "region_name": "Dallas Distribution Center", "quantity": 360, "snapshot_date": snapshot_date},
        {"sku": "SKU-1003", "region_name": "Chicago Cross-Dock", "quantity": 1080, "snapshot_date": snapshot_date},
        {"sku": "SKU-1004", "region_name": "Los Angeles Fulfillment Hub", "quantity": 510, "snapshot_date": snapshot_date},
        {"sku": "SKU-1005", "region_name": "Los Angeles Fulfillment Hub", "quantity": 1380, "snapshot_date": snapshot_date},
    ]


def _build_supplier_shipments(snapshot_date: date) -> list[dict[str, object]]:
    """Builds active shipment rows around the current operating window."""

    return [
        {"sku": "SKU-1001", "supplier_name": "Beta Micro Devices", "expected_date": snapshot_date + timedelta(days=2), "actual_date": None, "quantity": 240, "status": "in_transit"},
        {"sku": "SKU-1002", "supplier_name": "Beta Micro Devices", "expected_date": snapshot_date - timedelta(days=2), "actual_date": snapshot_date, "quantity": 90, "status": "delayed"},
        {"sku": "SKU-1003", "supplier_name": "Crown Household Goods", "expected_date": snapshot_date - timedelta(days=1), "actual_date": snapshot_date - timedelta(days=1), "quantity": 180, "status": "delivered"},
        {"sku": "SKU-1004", "supplier_name": "Alpha Plastics", "expected_date": snapshot_date + timedelta(days=3), "actual_date": None, "quantity": 140, "status": "in_transit"},
        {"sku": "SKU-1005", "supplier_name": "Alpha Plastics", "expected_date": snapshot_date - timedelta(days=4), "actual_date": snapshot_date - timedelta(days=4), "quantity": 420, "status": "delivered"},
    ]


@task(name="extract_seed_supply_data")
def extract_seed_supply_data() -> dict[str, list[dict[str, object]]]:
    """Returns deterministic seed data for the local pipeline."""

    snapshot_date = date.today() - timedelta(days=1)
    return {
        "regions": list(REGIONS),
        "products": list(PRODUCTS),
        "inventory_snapshots": _build_inventory_snapshots(snapshot_date),
        "daily_sales": _build_daily_sales(snapshot_date),
        "supplier_shipments": _build_supplier_shipments(snapshot_date),
    }
