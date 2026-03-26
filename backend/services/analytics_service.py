"""Focused analytics helpers that sit outside the larger DB helper module."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db_models import DailySale, Product, Region


async def get_analytics_filter_options(session: AsyncSession) -> dict[str, object]:
    """Returns regions, products, and categories used by the analytics filter bar."""

    product_rows = (
        await session.execute(
            select(Product.id, Product.name, Product.sku, Product.category).order_by(Product.category.asc(), Product.name.asc())
        )
    ).all()
    region_rows = (await session.execute(select(Region.id, Region.name).order_by(Region.name.asc()))).all()

    categories = sorted({str(category) for _, _, _, category in product_rows if category})

    return {
        "regions": [
            {
                "region_id": region_id,
                "region_name": region_name,
            }
            for region_id, region_name in region_rows
        ],
        "products": [
            {
                "product_id": product_id,
                "product_name": product_name,
                "sku": sku,
                "category": category,
            }
            for product_id, product_name, sku, category in product_rows
        ],
        "categories": categories,
    }


async def get_regional_growth(session: AsyncSession) -> list[dict[str, object]]:
    """Returns the latest month-over-month revenue growth for each region."""

    sales_month = func.date_trunc("month", DailySale.sale_date)
    statement = (
        select(
            Region.id,
            Region.name,
            sales_month.label("sales_month"),
            func.sum(func.coalesce(DailySale.revenue, 0)).label("revenue"),
        )
        .join(Region, DailySale.region_id == Region.id)
        .group_by(Region.id, Region.name, sales_month)
        .order_by(Region.name.asc(), sales_month.desc())
    )
    rows = (await session.execute(statement)).all()

    grouped_rows: dict[object, list[tuple[object, object, float]]] = {}
    for region_id, region_name, month_value, revenue in rows:
        month_date = month_value.date() if hasattr(month_value, "date") else month_value
        grouped_rows.setdefault(region_id, []).append((region_name, month_date, float(revenue or 0)))

    payload: list[dict[str, object]] = []
    for region_id, entries in grouped_rows.items():
        current_region_name, current_month, current_revenue = entries[0]
        previous_entry = entries[1] if len(entries) > 1 else None
        previous_month = previous_entry[1] if previous_entry else None
        previous_revenue = float(previous_entry[2]) if previous_entry else 0.0
        growth_pct = round(((current_revenue - previous_revenue) / previous_revenue) * 100, 2) if previous_revenue else 0.0

        payload.append(
            {
                "region_id": region_id,
                "region_name": current_region_name,
                "current_month": current_month,
                "previous_month": previous_month,
                "revenue": round(current_revenue, 2),
                "previous_revenue": round(previous_revenue, 2),
                "growth_pct": growth_pct,
            }
        )

    return sorted(payload, key=lambda item: str(item["region_name"]))
