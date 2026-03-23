"""Async database helpers for SupplyIQ."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models.db_models import Base, ForecastRun, InventoryAlert, InventorySnapshot, Product, Region, Supplier
from backend.models.schemas import (
    AlertItem,
    ForecastRecordResponse,
    InventoryPositionItem,
    InventoryRebalanceRequest,
    InventoryRebalanceResponse,
    KPI,
    SupplierPerformanceItem,
)
from backend.settings import get_settings

settings = get_settings()


def build_async_database_url(database_url: str) -> str:
    """Converts SQLAlchemy sync PostgreSQL URLs into asyncpg URLs."""

    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


engine = create_async_engine(build_async_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


async def initialize_database() -> None:
    """Creates the database tables if they do not exist yet."""

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_database_engine() -> None:
    """Closes the shared async SQLAlchemy engine."""

    await engine.dispose()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields an async SQLAlchemy session to FastAPI endpoints."""

    async with SessionLocal() as session:
        yield session


async def _load_current_inventory_rows(
    session: AsyncSession,
    region_code: str | None = None,
) -> list[tuple[InventorySnapshot, Product, Region, Supplier]]:
    """Loads the latest inventory row for each product-region combination."""

    statement = (
        select(InventorySnapshot, Product, Region, Supplier)
        .join(Product, InventorySnapshot.product_id == Product.id)
        .join(Region, InventorySnapshot.region_id == Region.id)
        .join(Supplier, Product.supplier_id == Supplier.id)
        .order_by(InventorySnapshot.snapshot_at.desc())
    )
    if region_code is not None:
        statement = statement.where(Region.region_code == region_code)

    rows = (await session.execute(statement)).all()
    latest_rows: dict[tuple[UUID, UUID], tuple[InventorySnapshot, Product, Region, Supplier]] = {}
    for snapshot, product, region, supplier in rows:
        latest_rows.setdefault((snapshot.product_id, snapshot.region_id), (snapshot, product, region, supplier))
    return list(latest_rows.values())


async def get_inventory_context(
    session: AsyncSession,
    *,
    product_id: UUID,
    region_id: UUID,
) -> tuple[InventorySnapshot, Product, Region, Supplier]:
    """Returns the latest inventory context for a product-region pair."""

    for snapshot, product, region, supplier in await _load_current_inventory_rows(session):
        if product.id == product_id and region.id == region_id:
            return snapshot, product, region, supplier
    raise LookupError("Inventory context was not found for the requested product and region.")


async def build_analytics_kpis(
    session: AsyncSession,
    *,
    region_code: str | None = None,
) -> list[KPI]:
    """Builds the analytics KPI collection from current inventory data."""

    rows = await _load_current_inventory_rows(session, region_code=region_code)
    total_inventory_units = sum(snapshot.quantity_on_hand for snapshot, *_ in rows)
    total_reserved_units = sum(snapshot.quantity_reserved for snapshot, *_ in rows)
    below_reorder = len([row for row in rows if row[0].quantity_on_hand + row[0].inbound_units < row[1].reorder_point])
    average_cover = (
        round(
            sum(row[0].quantity_on_hand / max(row[1].base_daily_demand, 1) for row in rows) / len(rows),
            1,
        )
        if rows
        else 0.0
    )

    return [
        KPI(label="Inventory Units", value=total_inventory_units, change_note="Current on-hand inventory across active positions."),
        KPI(label="Reserved Units", value=total_reserved_units, change_note="Units already committed to outbound demand."),
        KPI(label="At-Risk Positions", value=below_reorder, change_note="Locations currently below modeled reorder thresholds."),
        KPI(label="Avg. Days of Cover", value=average_cover, change_note="Average cover based on base daily demand.", unit="days"),
    ]


async def build_supplier_performance(
    session: AsyncSession,
    *,
    region_code: str | None = None,
) -> list[SupplierPerformanceItem]:
    """Builds supplier performance metrics from current inventory state."""

    rows = await _load_current_inventory_rows(session, region_code=region_code)
    grouped: dict[UUID, list[tuple[InventorySnapshot, Product, Region, Supplier]]] = {}
    for row in rows:
        grouped.setdefault(row[3].id, []).append(row)

    items: list[SupplierPerformanceItem] = []
    for supplier_rows in grouped.values():
        supplier = supplier_rows[0][3]
        reliability_score = float(supplier.reliability_score)
        fill_rate_pct = round(
            sum(
                min((snapshot.quantity_on_hand + snapshot.inbound_units) / max(product.reorder_point, 1), 1.2)
                for snapshot, product, *_ in supplier_rows
            )
            / len(supplier_rows)
            * 100,
            1,
        )
        risk_level = "critical" if reliability_score < 0.82 else "high" if reliability_score < 0.88 else "medium" if reliability_score < 0.93 else "low"
        items.append(
            SupplierPerformanceItem(
                supplier_id=supplier.id,
                supplier_code=supplier.supplier_code,
                name=supplier.name,
                reliability_score=reliability_score,
                lead_time_days=supplier.lead_time_days,
                active_products=len(supplier_rows),
                fill_rate_pct=fill_rate_pct,
                risk_level=risk_level,
            )
        )

    return sorted(items, key=lambda item: (item.risk_level, item.fill_rate_pct))


async def list_alerts(
    session: AsyncSession,
    *,
    region_code: str | None = None,
    severity: str | None = None,
    limit: int = 6,
) -> list[AlertItem]:
    """Returns active alerts ordered by recency."""

    statement = (
        select(InventoryAlert, Product, Region)
        .join(Product, InventoryAlert.product_id == Product.id)
        .join(Region, InventoryAlert.region_id == Region.id)
        .order_by(InventoryAlert.created_at.desc())
    )
    if region_code is not None:
        statement = statement.where(Region.region_code == region_code)
    if severity is not None:
        statement = statement.where(InventoryAlert.severity == severity)

    rows = (await session.execute(statement.limit(limit))).all()
    return [
        AlertItem(
            alert_id=alert.id,
            product_id=product.id,
            region_id=region.id,
            product_name=product.name,
            region_name=region.name,
            severity=alert.severity,
            message=alert.message,
            triggered_by=alert.triggered_by,
            created_at=alert.created_at,
        )
        for alert, product, region in rows
    ]


async def list_inventory_positions(
    session: AsyncSession,
    *,
    region_code: str | None = None,
    below_reorder_only: bool = False,
    limit: int = 25,
) -> list[InventoryPositionItem]:
    """Returns latest inventory positions with derived risk labels."""

    rows = await _load_current_inventory_rows(session, region_code=region_code)
    items: list[InventoryPositionItem] = []
    for snapshot, product, region, _supplier in rows:
        available_units = snapshot.quantity_on_hand + snapshot.inbound_units - snapshot.quantity_reserved
        if below_reorder_only and available_units >= product.reorder_point:
            continue
        days_of_cover = round(snapshot.quantity_on_hand / max(product.base_daily_demand, 1), 1)
        risk_level = "critical" if available_units < product.reorder_point * 0.65 else "high" if available_units < product.reorder_point else "medium" if days_of_cover < 18 else "low"
        items.append(
            InventoryPositionItem(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                region_id=region.id,
                region_name=region.name,
                quantity_on_hand=snapshot.quantity_on_hand,
                quantity_reserved=snapshot.quantity_reserved,
                inbound_units=snapshot.inbound_units,
                reorder_point=product.reorder_point,
                days_of_cover=days_of_cover,
                risk_level=risk_level,
            )
        )

    return items[:limit]


def _to_forecast_response(record: ForecastRun, product: Product, region: Region) -> ForecastRecordResponse:
    """Maps ORM objects into the forecast response schema."""

    return ForecastRecordResponse(
        forecast_id=record.id,
        product_id=product.id,
        region_id=region.id,
        product_name=product.name,
        region_name=region.name,
        horizon_days=record.horizon_days,
        predicted_demand_units=record.predicted_demand_units,
        lower_bound_units=record.lower_bound_units,
        upper_bound_units=record.upper_bound_units,
        stockout_probability_pct=float(record.stockout_probability_pct),
        recommended_reorder_units=record.recommended_reorder_units,
        model_version=record.model_version,
        generated_at=record.generated_at,
    )


async def save_forecast_run(
    session: AsyncSession,
    *,
    product: Product,
    region: Region,
    horizon_days: int,
    predicted_demand_units: int,
    lower_bound_units: int,
    upper_bound_units: int,
    stockout_probability_pct: float,
    recommended_reorder_units: int,
    model_version: str,
) -> ForecastRecordResponse:
    """Persists a generated forecast and returns the response schema."""

    record = ForecastRun(
        product_id=product.id,
        region_id=region.id,
        horizon_days=horizon_days,
        predicted_demand_units=predicted_demand_units,
        lower_bound_units=lower_bound_units,
        upper_bound_units=upper_bound_units,
        stockout_probability_pct=stockout_probability_pct,
        recommended_reorder_units=recommended_reorder_units,
        model_version=model_version,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _to_forecast_response(record, product, region)


async def get_latest_forecast(
    session: AsyncSession,
    *,
    product_id: UUID,
    region_id: UUID,
) -> ForecastRecordResponse | None:
    """Returns the newest forecast for a product-region pair."""

    statement = (
        select(ForecastRun, Product, Region)
        .join(Product, ForecastRun.product_id == Product.id)
        .join(Region, ForecastRun.region_id == Region.id)
        .where(ForecastRun.product_id == product_id, ForecastRun.region_id == region_id)
        .order_by(ForecastRun.generated_at.desc())
    )
    row = (await session.execute(statement)).first()
    if row is None:
        return None

    record, product, region = row
    return _to_forecast_response(record, product, region)


async def get_forecast_history(session: AsyncSession, *, product_id: UUID) -> list[ForecastRecordResponse]:
    """Returns forecast history for a product across all regions."""

    statement = (
        select(ForecastRun, Product, Region)
        .join(Product, ForecastRun.product_id == Product.id)
        .join(Region, ForecastRun.region_id == Region.id)
        .where(ForecastRun.product_id == product_id)
        .order_by(ForecastRun.generated_at.desc())
    )
    rows = (await session.execute(statement)).all()
    return [_to_forecast_response(record, product, region) for record, product, region in rows]


async def rebalance_inventory(
    session: AsyncSession,
    request: InventoryRebalanceRequest,
) -> InventoryRebalanceResponse:
    """Creates post-transfer inventory snapshots for the source and target regions."""

    source_snapshot, source_product, _source_region, _source_supplier = await get_inventory_context(
        session,
        product_id=request.product_id,
        region_id=request.source_region_id,
    )
    target_snapshot, _target_product, _target_region, _target_supplier = await get_inventory_context(
        session,
        product_id=request.product_id,
        region_id=request.target_region_id,
    )

    available_units = source_snapshot.quantity_on_hand - source_snapshot.quantity_reserved
    if request.quantity_units > available_units:
        raise ValueError("Requested transfer exceeds available source inventory.")

    source_record = InventorySnapshot(
        product_id=request.product_id,
        region_id=request.source_region_id,
        quantity_on_hand=source_snapshot.quantity_on_hand - request.quantity_units,
        quantity_reserved=source_snapshot.quantity_reserved,
        inbound_units=source_snapshot.inbound_units,
    )
    target_record = InventorySnapshot(
        product_id=request.product_id,
        region_id=request.target_region_id,
        quantity_on_hand=target_snapshot.quantity_on_hand + request.quantity_units,
        quantity_reserved=target_snapshot.quantity_reserved,
        inbound_units=target_snapshot.inbound_units,
    )
    session.add_all([source_record, target_record])
    await session.commit()

    return InventoryRebalanceResponse(
        generated_at=datetime.now(timezone.utc),
        product_id=source_product.id,
        source_region_id=request.source_region_id,
        target_region_id=request.target_region_id,
        quantity_units=request.quantity_units,
        status="completed",
    )
