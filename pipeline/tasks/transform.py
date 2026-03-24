"""Transformation tasks for SupplyIQ pipeline."""

from __future__ import annotations

try:
    from prefect import task
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def task(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator


@task(name="transform_supply_data")
def transform_supply_data(raw_data: dict[str, list[dict[str, object]]]) -> dict[str, list[dict[str, object]]]:
    """Normalizes extracted seed data into the persisted schema shape."""

    return {
        "regions": list(raw_data["regions"]),
        "products": list(raw_data["products"]),
        "inventory_snapshots": list(raw_data["inventory_snapshots"]),
        "daily_sales": list(raw_data["daily_sales"]),
        "supplier_shipments": list(raw_data["supplier_shipments"]),
    }
