"""Load tasks for SupplyIQ pipeline."""

from __future__ import annotations

import psycopg
from prefect import task

from pipeline.tasks.database import build_postgres_dsn, get_pipeline_database_url


def _upsert_supplier(cursor: psycopg.Cursor[tuple[object, ...]], payload: dict[str, object]) -> object:
    """Upserts a supplier row and returns its primary key."""

    cursor.execute(
        """
        SELECT id
        FROM suppliers
        WHERE supplier_code = %s
        """,
        (payload["supplier_code"],),
    )
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute(
            """
            UPDATE suppliers
            SET name = %s,
                country = %s,
                reliability_score = %s,
                lead_time_days = %s
            WHERE id = %s
            """,
            (
                payload["name"],
                payload["country"],
                payload["reliability_score"],
                payload["lead_time_days"],
                existing[0],
            ),
        )
        return existing[0]

    cursor.execute(
        """
        INSERT INTO suppliers (supplier_code, name, country, reliability_score, lead_time_days)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            payload["supplier_code"],
            payload["name"],
            payload["country"],
            payload["reliability_score"],
            payload["lead_time_days"],
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Supplier insert did not return an id.")
    return created[0]


def _upsert_region(cursor: psycopg.Cursor[tuple[object, ...]], payload: dict[str, object]) -> object:
    """Upserts a region row and returns its primary key."""

    cursor.execute(
        """
        SELECT id
        FROM regions
        WHERE region_code = %s
        """,
        (payload["region_code"],),
    )
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute(
            """
            UPDATE regions
            SET name = %s,
                market = %s,
                risk_factor = %s
            WHERE id = %s
            """,
            (
                payload["name"],
                payload["market"],
                payload["risk_factor"],
                existing[0],
            ),
        )
        return existing[0]

    cursor.execute(
        """
        INSERT INTO regions (region_code, name, market, risk_factor)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            payload["region_code"],
            payload["name"],
            payload["market"],
            payload["risk_factor"],
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Region insert did not return an id.")
    return created[0]


def _upsert_product(
    cursor: psycopg.Cursor[tuple[object, ...]],
    payload: dict[str, object],
    supplier_id: object,
) -> object:
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
                supplier_id = %s,
                unit_cost = %s,
                reorder_point = %s,
                base_daily_demand = %s
            WHERE id = %s
            """,
            (
                payload["name"],
                payload["category"],
                supplier_id,
                payload["unit_cost"],
                payload["reorder_point"],
                payload["base_daily_demand"],
                existing[0],
            ),
        )
        return existing[0]

    cursor.execute(
        """
        INSERT INTO products (sku, name, category, supplier_id, unit_cost, reorder_point, base_daily_demand)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            payload["sku"],
            payload["name"],
            payload["category"],
            supplier_id,
            payload["unit_cost"],
            payload["reorder_point"],
            payload["base_daily_demand"],
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Product insert did not return an id.")
    return created[0]


def _insert_alert(
    cursor: psycopg.Cursor[tuple[object, ...]],
    *,
    product_id: object,
    region_id: object,
    payload: dict[str, object],
) -> None:
    """Inserts an alert row with explicit defaults required by direct SQL writes."""

    cursor.execute(
        """
        INSERT INTO inventory_alerts (product_id, region_id, severity, message, triggered_by, acknowledged)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            product_id,
            region_id,
            str(payload["severity"]),
            str(payload["message"]),
            str(payload["triggered_by"]),
            False,
        ),
    )


@task(name="load_supply_data")
def load_supply_data(transformed_data: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    """Upserts seed data into PostgreSQL and returns load counts."""

    counts = {"suppliers": 0, "regions": 0, "products": 0, "inventory": 0, "alerts": 0}
    supplier_ids: dict[str, object] = {}
    region_ids: dict[str, object] = {}
    product_ids: dict[str, object] = {}
    database_dsn = build_postgres_dsn(get_pipeline_database_url())

    with psycopg.connect(database_dsn) as connection:
        with connection.cursor() as cursor:
            for payload in transformed_data["suppliers"]:
                supplier_ids[str(payload["supplier_code"])] = _upsert_supplier(cursor, payload)
                counts["suppliers"] += 1

            for payload in transformed_data["regions"]:
                region_ids[str(payload["region_code"])] = _upsert_region(cursor, payload)
                counts["regions"] += 1

            for payload in transformed_data["products"]:
                supplier_id = supplier_ids[str(payload["supplier_code"])]
                product_ids[str(payload["sku"])] = _upsert_product(cursor, payload, supplier_id)
                counts["products"] += 1

            for payload in transformed_data["inventory"]:
                cursor.execute(
                    """
                    INSERT INTO inventory_snapshots (product_id, region_id, quantity_on_hand, quantity_reserved, inbound_units)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        product_ids[str(payload["sku"])],
                        region_ids[str(payload["region_code"])],
                        int(payload["quantity_on_hand"]),
                        int(payload["quantity_reserved"]),
                        int(payload["inbound_units"]),
                    ),
                )
                counts["inventory"] += 1

            for payload in transformed_data.get("alerts", []):
                _insert_alert(
                    cursor,
                    product_id=product_ids[str(payload["sku"])],
                    region_id=region_ids[str(payload["region_code"])],
                    payload=payload,
                )
                counts["alerts"] += 1

        connection.commit()

    return counts
