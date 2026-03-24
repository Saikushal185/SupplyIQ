"""Load tasks for SupplyIQ pipeline."""

from __future__ import annotations

from typing import Any

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


def _upsert_region(cursor: Any, payload: dict[str, object]) -> object:
    """Upserts a region row and returns its primary key."""

    cursor.execute(
        """
        SELECT id
        FROM regions
        WHERE name = %s
        """,
        (payload["name"],),
    )
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute(
            """
            UPDATE regions
            SET country = %s,
                timezone = %s
            WHERE id = %s
            """,
            (
                payload["country"],
                payload["timezone"],
                existing[0],
            ),
        )
        return existing[0]

    cursor.execute(
        """
        INSERT INTO regions (name, country, timezone)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (
            payload["name"],
            payload["country"],
            payload["timezone"],
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Region insert did not return an id.")
    return created[0]


def _upsert_product(cursor: Any, payload: dict[str, object]) -> object:
    """Upserts a product row and returns its primary key."""

    cursor.execute(
        """
        SELECT id
        FROM products
        WHERE sku = %s
        """,
        (payload["sku"],),
    )
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute(
            """
            UPDATE products
            SET name = %s,
                category = %s,
                unit_cost = %s,
                reorder_point = %s
            WHERE id = %s
            """,
            (
                payload["name"],
                payload["category"],
                payload["unit_cost"],
                payload["reorder_point"],
                existing[0],
            ),
        )
        return existing[0]

    cursor.execute(
        """
        INSERT INTO products (sku, name, category, unit_cost, reorder_point)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            payload["sku"],
            payload["name"],
            payload["category"],
            payload["unit_cost"],
            payload["reorder_point"],
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Product insert did not return an id.")
    return created[0]


def _insert_inventory_snapshot(cursor: Any, payload: dict[str, object]) -> None:
    """Upserts an inventory snapshot using the exact schema keys."""

    cursor.execute(
        """
        INSERT INTO inventory_snapshots (product_id, region_id, quantity, snapshot_date)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (product_id, region_id, snapshot_date)
        DO UPDATE SET quantity = EXCLUDED.quantity
        """,
        (
            payload["product_id"],
            payload["region_id"],
            payload["quantity"],
            payload["snapshot_date"],
        ),
    )


def _upsert_daily_sale(cursor: Any, payload: dict[str, object]) -> None:
    """Upserts a daily sales row using product, region, and sale date as the seed key."""

    cursor.execute(
        """
        SELECT id
        FROM daily_sales
        WHERE product_id = %s
          AND region_id = %s
          AND sale_date = %s
        """,
        (payload["product_id"], payload["region_id"], payload["sale_date"]),
    )
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute(
            """
            UPDATE daily_sales
            SET units_sold = %s,
                revenue = %s,
                weather_temp = %s,
                traffic_index = %s
            WHERE id = %s
            """,
            (
                payload["units_sold"],
                payload["revenue"],
                payload["weather_temp"],
                payload["traffic_index"],
                existing[0],
            ),
        )
        return

    cursor.execute(
        """
        INSERT INTO daily_sales (product_id, region_id, sale_date, units_sold, revenue, weather_temp, traffic_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            payload["product_id"],
            payload["region_id"],
            payload["sale_date"],
            payload["units_sold"],
            payload["revenue"],
            payload["weather_temp"],
            payload["traffic_index"],
        ),
    )


def _upsert_supplier_shipment(cursor: Any, payload: dict[str, object]) -> None:
    """Upserts a supplier shipment using product, supplier, and expected date as the seed key."""

    cursor.execute(
        """
        SELECT id
        FROM supplier_shipments
        WHERE product_id = %s
          AND supplier_name = %s
          AND expected_date = %s
        """,
        (payload["product_id"], payload["supplier_name"], payload["expected_date"]),
    )
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute(
            """
            UPDATE supplier_shipments
            SET actual_date = %s,
                quantity = %s,
                status = %s
            WHERE id = %s
            """,
            (
                payload["actual_date"],
                payload["quantity"],
                payload["status"],
                existing[0],
            ),
        )
        return

    cursor.execute(
        """
        INSERT INTO supplier_shipments (product_id, supplier_name, expected_date, actual_date, quantity, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            payload["product_id"],
            payload["supplier_name"],
            payload["expected_date"],
            payload["actual_date"],
            payload["quantity"],
            payload["status"],
        ),
    )


@task(name="load_supply_data")
def load_supply_data(transformed_data: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    """Upserts seed data into PostgreSQL and returns load counts."""

    if psycopg is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("psycopg must be installed to run pipeline database loads.")

    counts = {
        "regions": 0,
        "products": 0,
        "inventory_snapshots": 0,
        "daily_sales": 0,
        "supplier_shipments": 0,
    }
    region_ids: dict[str, object] = {}
    product_ids: dict[str, object] = {}
    database_dsn = build_postgres_dsn(get_pipeline_database_url())

    with psycopg.connect(database_dsn) as connection:
        with connection.cursor() as cursor:
            for payload in transformed_data["regions"]:
                region_ids[str(payload["name"])] = _upsert_region(cursor, payload)
                counts["regions"] += 1

            for payload in transformed_data["products"]:
                product_ids[str(payload["sku"])] = _upsert_product(cursor, payload)
                counts["products"] += 1

            for payload in transformed_data["inventory_snapshots"]:
                _insert_inventory_snapshot(
                    cursor,
                    {
                        "product_id": product_ids[str(payload["sku"])],
                        "region_id": region_ids[str(payload["region_name"])],
                        "quantity": int(payload["quantity"]),
                        "snapshot_date": str(payload["snapshot_date"]),
                    },
                )
                counts["inventory_snapshots"] += 1

            for payload in transformed_data["daily_sales"]:
                _upsert_daily_sale(
                    cursor,
                    {
                        "product_id": product_ids[str(payload["sku"])],
                        "region_id": region_ids[str(payload["region_name"])],
                        "sale_date": str(payload["sale_date"]),
                        "units_sold": int(payload["units_sold"]),
                        "revenue": payload["revenue"],
                        "weather_temp": payload["weather_temp"],
                        "traffic_index": payload["traffic_index"],
                    },
                )
                counts["daily_sales"] += 1

            for payload in transformed_data["supplier_shipments"]:
                _upsert_supplier_shipment(
                    cursor,
                    {
                        "product_id": product_ids[str(payload["sku"])],
                        "supplier_name": str(payload["supplier_name"]),
                        "expected_date": str(payload["expected_date"]) if payload["expected_date"] else None,
                        "actual_date": str(payload["actual_date"]) if payload["actual_date"] else None,
                        "quantity": int(payload["quantity"]) if payload["quantity"] is not None else None,
                        "status": str(payload["status"]) if payload["status"] is not None else None,
                    },
                )
                counts["supplier_shipments"] += 1

        connection.commit()

    return counts
