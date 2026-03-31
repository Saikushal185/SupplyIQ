"""Shared catalog and regional reference data for SupplyIQ."""

from __future__ import annotations

DEFAULT_PRODUCTS: list[dict[str, object]] = [
    {"sku": "ELEC-100", "name": "Handheld Scanner", "category": "electronics", "unit_cost": 149.0, "reorder_point": 180, "base_demand": 32},
    {"sku": "ELEC-101", "name": "RFID Reader", "category": "electronics", "unit_cost": 189.0, "reorder_point": 165, "base_demand": 28},
    {"sku": "ELEC-102", "name": "Thermal Label Printer", "category": "electronics", "unit_cost": 229.0, "reorder_point": 140, "base_demand": 24},
    {"sku": "ELEC-103", "name": "Docking Station", "category": "electronics", "unit_cost": 129.0, "reorder_point": 170, "base_demand": 26},
    {"sku": "ELEC-104", "name": "Warehouse Tablet", "category": "electronics", "unit_cost": 319.0, "reorder_point": 120, "base_demand": 18},
    {"sku": "APP-200", "name": "Safety Gloves", "category": "apparel", "unit_cost": 18.0, "reorder_point": 320, "base_demand": 52},
    {"sku": "APP-201", "name": "Reflective Vest", "category": "apparel", "unit_cost": 24.0, "reorder_point": 280, "base_demand": 41},
    {"sku": "APP-202", "name": "Steel-Toe Boots", "category": "apparel", "unit_cost": 74.0, "reorder_point": 150, "base_demand": 20},
    {"sku": "APP-203", "name": "Cold Storage Jacket", "category": "apparel", "unit_cost": 88.0, "reorder_point": 110, "base_demand": 16},
    {"sku": "APP-204", "name": "Utility Apron", "category": "apparel", "unit_cost": 26.0, "reorder_point": 190, "base_demand": 23},
    {"sku": "FOOD-300", "name": "Energy Bars", "category": "food", "unit_cost": 9.0, "reorder_point": 430, "base_demand": 68},
    {"sku": "FOOD-301", "name": "Bottled Water Case", "category": "food", "unit_cost": 12.0, "reorder_point": 510, "base_demand": 74},
    {"sku": "FOOD-302", "name": "Instant Coffee Pods", "category": "food", "unit_cost": 16.0, "reorder_point": 360, "base_demand": 49},
    {"sku": "FOOD-303", "name": "Trail Mix Pack", "category": "food", "unit_cost": 11.0, "reorder_point": 390, "base_demand": 57},
    {"sku": "FOOD-304", "name": "Meal Replacement Shake", "category": "food", "unit_cost": 21.0, "reorder_point": 240, "base_demand": 38},
    {"sku": "HOME-400", "name": "Cleaning Wipes", "category": "household", "unit_cost": 14.0, "reorder_point": 350, "base_demand": 47},
    {"sku": "HOME-401", "name": "Storage Bin Set", "category": "household", "unit_cost": 33.0, "reorder_point": 220, "base_demand": 29},
    {"sku": "HOME-402", "name": "Paper Towel Pack", "category": "household", "unit_cost": 19.0, "reorder_point": 310, "base_demand": 44},
    {"sku": "HOME-403", "name": "Trash Bag Roll", "category": "household", "unit_cost": 8.0, "reorder_point": 470, "base_demand": 61},
    {"sku": "HOME-404", "name": "Air Filter", "category": "household", "unit_cost": 22.0, "reorder_point": 205, "base_demand": 27},
]

DEFAULT_REGIONS: list[dict[str, object]] = [
    {"name": "North", "city": "Chicago", "country": "United States", "timezone": "America/Chicago", "climate_temp": 11.0},
    {"name": "South", "city": "Houston", "country": "United States", "timezone": "America/Chicago", "climate_temp": 24.0},
    {"name": "East", "city": "New York", "country": "United States", "timezone": "America/New_York", "climate_temp": 14.0},
    {"name": "West", "city": "Los Angeles", "country": "United States", "timezone": "America/Los_Angeles", "climate_temp": 19.0},
    {"name": "Central", "city": "Denver", "country": "United States", "timezone": "America/Denver", "climate_temp": 12.0},
]

REGION_CITY_BY_NAME = {str(region["name"]): str(region["city"]) for region in DEFAULT_REGIONS}

