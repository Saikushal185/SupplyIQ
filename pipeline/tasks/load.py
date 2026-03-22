"""Load tasks for SupplyIQ pipeline."""

from __future__ import annotations

import os

from prefect import task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.models.db_models import InventoryAlert, InventorySnapshot, Product, Region, Supplier


def _session_factory() -> sessionmaker[Session]:
    """Creates a SQLAlchemy session factory for pipeline writes."""

    database_url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL")
    if not database_url:
        raise RuntimeError("PIPELINE_DATABASE_URL must be set for pipeline loading.")
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@task(name="load_supply_data")
def load_supply_data(transformed_data: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    """Upserts seed data into PostgreSQL and returns load counts."""

    SessionFactory = _session_factory()
    counts = {"suppliers": 0, "regions": 0, "products": 0, "inventory": 0, "alerts": 0}

    with SessionFactory() as session:
        supplier_ids: dict[str, object] = {}
        region_ids: dict[str, object] = {}
        product_ids: dict[str, object] = {}

        for payload in transformed_data["suppliers"]:
            record = session.execute(select(Supplier).where(Supplier.supplier_code == payload["supplier_code"])).scalar_one_or_none()
            if record is None:
                record = Supplier(**payload)
                session.add(record)
                session.flush()
            else:
                record.name = str(payload["name"])
                record.country = str(payload["country"])
                record.reliability_score = float(payload["reliability_score"])
                record.lead_time_days = int(payload["lead_time_days"])
            supplier_ids[str(payload["supplier_code"])] = record.id
            counts["suppliers"] += 1

        for payload in transformed_data["regions"]:
            record = session.execute(select(Region).where(Region.region_code == payload["region_code"])).scalar_one_or_none()
            if record is None:
                record = Region(**payload)
                session.add(record)
                session.flush()
            else:
                record.name = str(payload["name"])
                record.market = str(payload["market"])
                record.risk_factor = float(payload["risk_factor"])
            region_ids[str(payload["region_code"])] = record.id
            counts["regions"] += 1

        for payload in transformed_data["products"]:
            supplier_id = supplier_ids[str(payload["supplier_code"])]
            record = session.execute(select(Product).where(Product.sku == payload["sku"])).scalar_one_or_none()
            mapped_payload = {
                "sku": payload["sku"],
                "name": payload["name"],
                "category": payload["category"],
                "supplier_id": supplier_id,
                "unit_cost": payload["unit_cost"],
                "reorder_point": payload["reorder_point"],
                "base_daily_demand": payload["base_daily_demand"],
            }
            if record is None:
                record = Product(**mapped_payload)
                session.add(record)
                session.flush()
            else:
                record.name = str(payload["name"])
                record.category = str(payload["category"])
                record.supplier_id = supplier_id
                record.unit_cost = float(payload["unit_cost"])
                record.reorder_point = int(payload["reorder_point"])
                record.base_daily_demand = int(payload["base_daily_demand"])
            product_ids[str(payload["sku"])] = record.id
            counts["products"] += 1

        for payload in transformed_data["inventory"]:
            record = InventorySnapshot(
                product_id=product_ids[str(payload["sku"])],
                region_id=region_ids[str(payload["region_code"])],
                quantity_on_hand=int(payload["quantity_on_hand"]),
                quantity_reserved=int(payload["quantity_reserved"]),
                inbound_units=int(payload["inbound_units"]),
            )
            session.add(record)
            counts["inventory"] += 1

        for payload in transformed_data.get("alerts", []):
            record = InventoryAlert(
                product_id=product_ids[str(payload["sku"])],
                region_id=region_ids[str(payload["region_code"])],
                severity=str(payload["severity"]),
                message=str(payload["message"]),
                triggered_by=str(payload["triggered_by"]),
            )
            session.add(record)
            counts["alerts"] += 1

        session.commit()

    return counts
