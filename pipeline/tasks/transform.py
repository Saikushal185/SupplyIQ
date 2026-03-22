"""Transformation tasks for SupplyIQ pipeline."""

from __future__ import annotations

from prefect import task


@task(name="transform_supply_data")
def transform_supply_data(raw_data: dict[str, list[dict[str, object]]]) -> dict[str, list[dict[str, object]]]:
    """Adds derived alert rows to the extracted seed data."""

    product_lookup = {product["sku"]: product for product in raw_data["products"]}
    region_lookup = {region["region_code"]: region for region in raw_data["regions"]}

    alerts: list[dict[str, object]] = []
    for inventory_row in raw_data["inventory"]:
        product = product_lookup[inventory_row["sku"]]
        region = region_lookup[inventory_row["region_code"]]
        available_units = int(inventory_row["quantity_on_hand"]) + int(inventory_row["inbound_units"]) - int(inventory_row["quantity_reserved"])
        reorder_point = int(product["reorder_point"])
        if available_units < reorder_point:
            severity = "critical" if available_units < reorder_point * 0.7 else "high"
            alerts.append(
                {
                    "sku": product["sku"],
                    "region_code": region["region_code"],
                    "severity": severity,
                    "message": f"{product['name']} is below reorder threshold in {region['name']}.",
                    "triggered_by": "pipeline_reorder_monitor",
                }
            )

    return {**raw_data, "alerts": alerts}
