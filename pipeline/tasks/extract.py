"""Extraction tasks for SupplyIQ pipeline."""

from __future__ import annotations

from prefect import task


@task(name="extract_seed_supply_data")
def extract_seed_supply_data() -> dict[str, list[dict[str, object]]]:
    """Returns deterministic seed data for the local pipeline."""

    return {
        "suppliers": [
            {"supplier_code": "SUP-ALPHA", "name": "Alpha Plastics", "country": "Mexico", "reliability_score": 0.95, "lead_time_days": 8},
            {"supplier_code": "SUP-BETA", "name": "Beta Micro Devices", "country": "Taiwan", "reliability_score": 0.87, "lead_time_days": 16},
            {"supplier_code": "SUP-CROWN", "name": "Crown Household Goods", "country": "Vietnam", "reliability_score": 0.81, "lead_time_days": 22},
        ],
        "regions": [
            {"region_code": "US-SOUTH", "name": "Dallas Distribution Center", "market": "South", "risk_factor": 0.38},
            {"region_code": "US-MIDWEST", "name": "Chicago Cross-Dock", "market": "Midwest", "risk_factor": 0.44},
            {"region_code": "US-WEST", "name": "Los Angeles Fulfillment Hub", "market": "West", "risk_factor": 0.57},
        ],
        "products": [
            {"sku": "SKU-1001", "name": "Wireless Scanner", "category": "Electronics", "supplier_code": "SUP-BETA", "unit_cost": 82.0, "reorder_point": 640, "base_daily_demand": 58},
            {"sku": "SKU-1002", "name": "Smart Label Printer", "category": "Electronics", "supplier_code": "SUP-BETA", "unit_cost": 190.0, "reorder_point": 420, "base_daily_demand": 34},
            {"sku": "SKU-1003", "name": "Modular Shelf Bin", "category": "Storage", "supplier_code": "SUP-CROWN", "unit_cost": 24.0, "reorder_point": 760, "base_daily_demand": 84},
            {"sku": "SKU-1004", "name": "Cold Chain Sensor", "category": "Monitoring", "supplier_code": "SUP-ALPHA", "unit_cost": 68.0, "reorder_point": 390, "base_daily_demand": 41},
            {"sku": "SKU-1005", "name": "Packing Tape Roll", "category": "Packaging", "supplier_code": "SUP-ALPHA", "unit_cost": 6.4, "reorder_point": 1500, "base_daily_demand": 128},
        ],
        "inventory": [
            {"sku": "SKU-1001", "region_code": "US-SOUTH", "quantity_on_hand": 920, "quantity_reserved": 180, "inbound_units": 240},
            {"sku": "SKU-1002", "region_code": "US-SOUTH", "quantity_on_hand": 360, "quantity_reserved": 110, "inbound_units": 90},
            {"sku": "SKU-1003", "region_code": "US-MIDWEST", "quantity_on_hand": 1080, "quantity_reserved": 220, "inbound_units": 180},
            {"sku": "SKU-1004", "region_code": "US-WEST", "quantity_on_hand": 510, "quantity_reserved": 84, "inbound_units": 140},
            {"sku": "SKU-1005", "region_code": "US-WEST", "quantity_on_hand": 1380, "quantity_reserved": 260, "inbound_units": 420},
        ],
    }
