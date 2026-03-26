"""Local development data seeding helpers."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.db_models import DailySale, Product, Region, SupplierShipment
from pipeline.tasks.extract import extract_seed_supply_data

logger = logging.getLogger(__name__)


async def seed_local_analytics_data_if_needed(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seeds deterministic sales and shipment history when local tables are empty."""

    async with session_factory() as session:
        sales_count = int((await session.execute(select(func.count(DailySale.id)))).scalar_one())
        shipment_count = int((await session.execute(select(func.count(SupplierShipment.id)))).scalar_one())
        if sales_count > 0 and shipment_count > 0:
            return

        product_rows = (await session.execute(select(Product.id, Product.sku))).all()
        region_rows = (await session.execute(select(Region.id, Region.name))).all()
        product_ids = {sku: product_id for product_id, sku in product_rows}
        region_ids = {name: region_id for region_id, name in region_rows}
        if not product_ids or not region_ids:
            logger.warning("Skipping local analytics seed because product or region reference data is unavailable.")
            return

        seed_payload = extract_seed_supply_data.fn() if hasattr(extract_seed_supply_data, "fn") else extract_seed_supply_data()
        inserted_sales = 0
        inserted_shipments = 0

        if sales_count == 0:
            session.add_all(
                [
                    DailySale(
                        product_id=product_ids[str(row["sku"])],
                        region_id=region_ids[str(row["region_name"])],
                        sale_date=row["sale_date"],
                        units_sold=int(row["units_sold"]),
                        revenue=float(row["revenue"]),
                        weather_temp=float(row["weather_temp"]),
                        traffic_index=float(row["traffic_index"]),
                    )
                    for row in seed_payload["daily_sales"]
                    if str(row["sku"]) in product_ids and str(row["region_name"]) in region_ids
                ]
            )
            inserted_sales = len(seed_payload["daily_sales"])

        if shipment_count == 0:
            session.add_all(
                [
                    SupplierShipment(
                        product_id=product_ids[str(row["sku"])],
                        supplier_name=str(row["supplier_name"]),
                        expected_date=row["expected_date"],
                        actual_date=row["actual_date"],
                        quantity=int(row["quantity"]) if row["quantity"] is not None else None,
                        status=str(row["status"]) if row["status"] is not None else None,
                    )
                    for row in seed_payload["supplier_shipments"]
                    if str(row["sku"]) in product_ids
                ]
            )
            inserted_shipments = len(seed_payload["supplier_shipments"])

        if inserted_sales or inserted_shipments:
            await session.commit()
            logger.info(
                "Seeded local analytics data: %s daily_sales rows, %s supplier_shipments rows.",
                inserted_sales,
                inserted_shipments,
            )
