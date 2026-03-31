"""Extraction tasks for SupplyIQ pipeline."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    httpx = None  # type: ignore[assignment]

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    np = None  # type: ignore[assignment]

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    psycopg = None  # type: ignore[assignment]

try:
    from prefect import task
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def task(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator

from pipeline.tasks.database import build_postgres_dsn, get_pipeline_database_url
from pipeline.tasks.reference_data import DEFAULT_PRODUCTS, DEFAULT_REGIONS, REGION_CITY_BY_NAME


def seasonal_multiplier(category: str, month: int) -> float:
    """Returns a category-aware seasonal demand adjustment for the given month."""

    normalized_category = category.lower()
    if normalized_category == "electronics":
        holiday_boost = {11: 18.0, 12: 24.0, 1: 6.0}
        return holiday_boost.get(month, 1.5 if month in {6, 7} else 4.0)
    if normalized_category == "apparel":
        return 10.0 if month in {10, 11, 12, 1} else 4.0
    if normalized_category == "food":
        return 6.0
    if normalized_category == "household":
        return 9.0 if month in {3, 4, 5} else 5.0
    return 4.0


def time_of_day_traffic_factor(run_at: datetime) -> float:
    """Returns a traffic multiplier based on the pipeline execution hour."""

    hour = run_at.hour
    if 6 <= hour < 10:
        return 1.35
    if 10 <= hour < 16:
        return 1.1
    if 16 <= hour < 20:
        return 1.25
    return 0.65


def _coerce_run_at(run_at: datetime | None = None) -> datetime:
    """Normalizes extraction timestamps to UTC-aware datetimes."""

    resolved = run_at or datetime.now(UTC)
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=UTC)
    return resolved.astimezone(UTC)


def _get_rng(rng: Any | None = None) -> Any:
    """Builds or returns the random generator used for simulation."""

    if rng is not None:
        return rng
    if np is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("numpy must be installed to generate ingestion demand signals.")
    return np.random.default_rng()


def _weather_fallback(region: dict[str, object], run_at: datetime) -> float:
    """Returns a deterministic regional fallback temperature when the API is unavailable."""

    baseline = float(region.get("climate_temp", 18.0))
    month_adjustment = {
        12: -8.0,
        1: -8.0,
        2: -6.5,
        3: -2.0,
        4: 1.0,
        5: 5.0,
        6: 8.0,
        7: 10.0,
        8: 9.5,
        9: 6.0,
        10: 2.5,
        11: -1.0,
    }
    return round(baseline + month_adjustment.get(run_at.month, 0.0), 2)


def fetch_weather_by_region(
    regions: list[dict[str, object]],
    *,
    api_key: str | None,
    run_at: datetime,
) -> dict[str, float]:
    """Fetches live temperatures from OpenWeatherMap, falling back to seasonal baselines."""

    if httpx is None or not api_key:
        return {
            str(region["region_id"]): _weather_fallback(region, run_at)
            for region in regions
        }

    weather_by_region: dict[str, float] = {}
    with httpx.Client(timeout=10.0) as client:
        for region in regions:
            city = str(region.get("city") or REGION_CITY_BY_NAME.get(str(region.get("name")), region.get("name", "")))
            try:
                response = client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": city,
                        "appid": api_key,
                        "units": "metric",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                weather_by_region[str(region["region_id"])] = round(float(payload["main"]["temp"]), 2)
            except Exception:  # pragma: no cover - exercised in live integration only
                weather_by_region[str(region["region_id"])] = _weather_fallback(region, run_at)
    return weather_by_region


def build_live_daily_sales_rows(
    *,
    products: list[dict[str, object]],
    regions: list[dict[str, object]],
    weather_by_region: dict[str, float],
    run_at: datetime,
    rng: Any | None = None,
) -> list[dict[str, object]]:
    """Generates a simulated daily sales row for every product-region pair."""

    generator = _get_rng(rng)
    rows: list[dict[str, object]] = []
    traffic_factor = time_of_day_traffic_factor(run_at)
    for product in products:
        base_demand = float(product.get("base_demand") or 24.0)
        category = str(product.get("category", "household"))
        seasonal_adjustment = seasonal_multiplier(category, run_at.month)
        for region in regions:
            noise = float(generator.normal(0.0, max(base_demand * 0.08, 1.0)))
            units_sold = max(
                int(round(base_demand + seasonal_adjustment + noise)),
                0,
            )
            traffic_index = round(float(generator.uniform(0.2, 0.9)) * traffic_factor, 4)
            rows.append(
                {
                    "product_id": product["product_id"],
                    "region_id": region["region_id"],
                    "sale_date": run_at.date(),
                    "units_sold": units_sold,
                    "weather_temp": weather_by_region[str(region["region_id"])],
                    "traffic_index": traffic_index,
                }
            )
    return rows


def _load_reference_data_from_database(run_at: datetime) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[tuple[str, str], int]]:
    """Loads products, regions, and latest opening inventory from PostgreSQL."""

    if psycopg is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("psycopg must be installed to load ingestion reference data.")

    sale_date = run_at.date()
    database_dsn = build_postgres_dsn(get_pipeline_database_url())
    products: list[dict[str, object]] = []
    regions: list[dict[str, object]] = []
    opening_inventory: dict[tuple[str, str], int] = {}

    with psycopg.connect(database_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    sku,
                    name,
                    category,
                    COALESCE(unit_cost, 0),
                    COALESCE(reorder_point, 0),
                    GREATEST(COALESCE(reorder_point, 0) * 0.35, 12)
                FROM products
                ORDER BY sku
                """
            )
            for product_id, sku, name, category, unit_cost, reorder_point, base_demand in cursor.fetchall():
                products.append(
                    {
                        "product_id": product_id,
                        "sku": sku,
                        "name": name,
                        "category": str(category or "household").lower(),
                        "unit_cost": float(unit_cost or 0),
                        "reorder_point": int(reorder_point or 0),
                        "base_demand": float(base_demand or 12),
                    }
                )

            cursor.execute(
                """
                SELECT id, name, country, timezone
                FROM regions
                ORDER BY name
                """
            )
            for region_id, name, country, timezone_name in cursor.fetchall():
                regions.append(
                    {
                        "region_id": region_id,
                        "name": name,
                        "country": country,
                        "timezone": timezone_name,
                        "city": REGION_CITY_BY_NAME.get(str(name), str(name)),
                    }
                )

            cursor.execute(
                """
                WITH ranked_snapshots AS (
                    SELECT
                        product_id,
                        region_id,
                        quantity,
                        snapshot_date,
                        ROW_NUMBER() OVER (
                            PARTITION BY product_id, region_id
                            ORDER BY snapshot_date DESC, id DESC
                        ) AS snapshot_rank
                    FROM inventory_snapshots
                    WHERE snapshot_date < %s
                )
                SELECT product_id, region_id, quantity
                FROM ranked_snapshots
                WHERE snapshot_rank = 1
                """,
                (sale_date,),
            )
            for product_id, region_id, quantity in cursor.fetchall():
                opening_inventory[(str(product_id), str(region_id))] = int(quantity or 0)

    return products, regions, opening_inventory


def _build_bootstrap_reference_data() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[tuple[str, str], int]]:
    """Builds in-memory fallback reference data for fresh local environments."""

    products = [
        {
            "product_id": product["sku"],
            **product,
        }
        for product in DEFAULT_PRODUCTS
    ]
    regions = [
        {
            "region_id": region["name"],
            **region,
        }
        for region in DEFAULT_REGIONS
    ]
    opening_inventory = {
        (str(product["product_id"]), str(region["region_id"])): int(float(product["reorder_point"]) * 1.8)
        for product in products
        for region in regions
    }
    return products, regions, opening_inventory


def _build_inventory_snapshots(
    *,
    products: list[dict[str, object]],
    regions: list[dict[str, object]],
    opening_inventory: dict[tuple[str, str], int],
    snapshot_date: date,
) -> list[dict[str, object]]:
    """Builds inventory opening rows for transformation and load steps."""

    rows: list[dict[str, object]] = []
    for product in products:
        default_opening = int(float(product.get("reorder_point") or 0) * 1.8) or 80
        for region in regions:
            rows.append(
                {
                    "product_id": product["product_id"],
                    "region_id": region["region_id"],
                    "snapshot_date": snapshot_date,
                    "opening_quantity": opening_inventory.get(
                        (str(product["product_id"]), str(region["region_id"])),
                        default_opening,
                    ),
                }
            )
    return rows


@task(name="extract_seed_supply_data")
def extract_seed_supply_data() -> dict[str, list[dict[str, object]]]:
    """Extracts the daily simulated sales inputs for the ingestion pipeline."""

    run_at = _coerce_run_at()
    try:
        products, regions, opening_inventory = _load_reference_data_from_database(run_at)
    except Exception:
        products, regions, opening_inventory = _build_bootstrap_reference_data()

    weather_by_region = fetch_weather_by_region(
        regions,
        api_key=os.getenv("OPENWEATHERMAP_API_KEY") or os.getenv("BACKEND_OPENWEATHERMAP_API_KEY"),
        run_at=run_at,
    )
    daily_sales = build_live_daily_sales_rows(
        products=products,
        regions=regions,
        weather_by_region=weather_by_region,
        run_at=run_at,
    )

    return {
        "products": products,
        "regions": regions,
        "daily_sales": daily_sales,
        "inventory_snapshots": _build_inventory_snapshots(
            products=products,
            regions=regions,
            opening_inventory=opening_inventory,
            snapshot_date=run_at.date(),
        ),
        "extracted_at": run_at.isoformat(),
    }
