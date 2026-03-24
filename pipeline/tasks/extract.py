"""Extraction tasks for SupplyIQ pipeline."""

from __future__ import annotations

try:
    from prefect import task
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def task(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator


@task(name="extract_seed_supply_data")
def extract_seed_supply_data() -> dict[str, list[dict[str, object]]]:
    """Returns deterministic seed data for the local pipeline."""

    return {
        "regions": [
            {"name": "Dallas Distribution Center", "country": "United States", "timezone": "America/Chicago"},
            {"name": "Chicago Cross-Dock", "country": "United States", "timezone": "America/Chicago"},
            {"name": "Los Angeles Fulfillment Hub", "country": "United States", "timezone": "America/Los_Angeles"},
        ],
        "products": [
            {"sku": "SKU-1001", "name": "Wireless Scanner", "category": "Electronics", "unit_cost": 82.0, "reorder_point": 640},
            {"sku": "SKU-1002", "name": "Smart Label Printer", "category": "Electronics", "unit_cost": 190.0, "reorder_point": 420},
            {"sku": "SKU-1003", "name": "Modular Shelf Bin", "category": "Storage", "unit_cost": 24.0, "reorder_point": 760},
            {"sku": "SKU-1004", "name": "Cold Chain Sensor", "category": "Monitoring", "unit_cost": 68.0, "reorder_point": 390},
            {"sku": "SKU-1005", "name": "Packing Tape Roll", "category": "Packaging", "unit_cost": 6.4, "reorder_point": 1500},
        ],
        "inventory_snapshots": [
            {"sku": "SKU-1001", "region_name": "Dallas Distribution Center", "quantity": 920, "snapshot_date": "2026-03-24"},
            {"sku": "SKU-1002", "region_name": "Dallas Distribution Center", "quantity": 360, "snapshot_date": "2026-03-24"},
            {"sku": "SKU-1003", "region_name": "Chicago Cross-Dock", "quantity": 1080, "snapshot_date": "2026-03-24"},
            {"sku": "SKU-1004", "region_name": "Los Angeles Fulfillment Hub", "quantity": 510, "snapshot_date": "2026-03-24"},
            {"sku": "SKU-1005", "region_name": "Los Angeles Fulfillment Hub", "quantity": 1380, "snapshot_date": "2026-03-24"},
        ],
        "daily_sales": [
            {"sku": "SKU-1001", "region_name": "Dallas Distribution Center", "sale_date": "2026-03-19", "units_sold": 61, "revenue": 5002.0, "weather_temp": 72.0, "traffic_index": 0.42},
            {"sku": "SKU-1001", "region_name": "Dallas Distribution Center", "sale_date": "2026-03-20", "units_sold": 58, "revenue": 4756.0, "weather_temp": 74.0, "traffic_index": 0.47},
            {"sku": "SKU-1002", "region_name": "Dallas Distribution Center", "sale_date": "2026-03-21", "units_sold": 33, "revenue": 6270.0, "weather_temp": 76.0, "traffic_index": 0.51},
            {"sku": "SKU-1002", "region_name": "Dallas Distribution Center", "sale_date": "2026-03-22", "units_sold": 36, "revenue": 6840.0, "weather_temp": 78.0, "traffic_index": 0.49},
            {"sku": "SKU-1003", "region_name": "Chicago Cross-Dock", "sale_date": "2026-03-19", "units_sold": 88, "revenue": 2112.0, "weather_temp": 49.0, "traffic_index": 0.38},
            {"sku": "SKU-1003", "region_name": "Chicago Cross-Dock", "sale_date": "2026-03-20", "units_sold": 86, "revenue": 2064.0, "weather_temp": 53.0, "traffic_index": 0.35},
            {"sku": "SKU-1004", "region_name": "Los Angeles Fulfillment Hub", "sale_date": "2026-03-21", "units_sold": 39, "revenue": 2652.0, "weather_temp": 68.0, "traffic_index": 0.58},
            {"sku": "SKU-1004", "region_name": "Los Angeles Fulfillment Hub", "sale_date": "2026-03-22", "units_sold": 44, "revenue": 2992.0, "weather_temp": 70.0, "traffic_index": 0.61},
            {"sku": "SKU-1005", "region_name": "Los Angeles Fulfillment Hub", "sale_date": "2026-03-23", "units_sold": 121, "revenue": 774.4, "weather_temp": 71.0, "traffic_index": 0.66},
            {"sku": "SKU-1005", "region_name": "Los Angeles Fulfillment Hub", "sale_date": "2026-03-24", "units_sold": 126, "revenue": 806.4, "weather_temp": 72.0, "traffic_index": 0.69},
        ],
        "supplier_shipments": [
            {"sku": "SKU-1001", "supplier_name": "Beta Micro Devices", "expected_date": "2026-03-26", "actual_date": None, "quantity": 240, "status": "in_transit"},
            {"sku": "SKU-1002", "supplier_name": "Beta Micro Devices", "expected_date": "2026-03-22", "actual_date": "2026-03-24", "quantity": 90, "status": "delayed"},
            {"sku": "SKU-1003", "supplier_name": "Crown Household Goods", "expected_date": "2026-03-23", "actual_date": "2026-03-23", "quantity": 180, "status": "delivered"},
            {"sku": "SKU-1004", "supplier_name": "Alpha Plastics", "expected_date": "2026-03-27", "actual_date": None, "quantity": 140, "status": "in_transit"},
            {"sku": "SKU-1005", "supplier_name": "Alpha Plastics", "expected_date": "2026-03-20", "actual_date": "2026-03-20", "quantity": 420, "status": "delivered"},
        ],
    }
