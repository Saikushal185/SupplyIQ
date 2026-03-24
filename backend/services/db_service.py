"""Async database helpers for SupplyIQ."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models.db_models import DailySale, ForecastRun, InventorySnapshot, Product, Region, SupplierShipment, Base
from backend.models.schemas import (
    AlertItem,
    DemandPoint,
    ForecastExplainabilityPayload,
    ForecastHistoryResponse,
    ForecastPayload,
    ForecastRecordResponse,
    InventoryPositionItem,
    InventoryRebalanceRequest,
    InventoryRebalanceResponse,
    KPI,
    SupplierPerformanceItem,
)
from backend.settings import get_settings

settings = get_settings()


@dataclass(slots=True)
class LatestInventoryRow:
    """Represents the latest stored inventory state for a product-region pair."""

    snapshot_id: UUID
    quantity: int
    snapshot_date: date
    product: Product
    region: Region


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


def _latest_inventory_subquery():
    """Builds a reusable subquery that ranks snapshots by recency."""

    return (
        select(
            InventorySnapshot.id.label("snapshot_id"),
            InventorySnapshot.product_id.label("product_id"),
            InventorySnapshot.region_id.label("region_id"),
            InventorySnapshot.quantity.label("quantity"),
            InventorySnapshot.snapshot_date.label("snapshot_date"),
            func.row_number()
            .over(
                partition_by=(InventorySnapshot.product_id, InventorySnapshot.region_id),
                order_by=(InventorySnapshot.snapshot_date.desc(), InventorySnapshot.id.desc()),
            )
            .label("snapshot_rank"),
        )
        .subquery()
    )


def _derive_risk_level(quantity: int, reorder_point: int | None) -> str:
    """Returns a compact risk label from inventory versus reorder point."""

    if reorder_point is None or reorder_point <= 0:
        return "low"
    if quantity < reorder_point * 0.5:
        return "critical"
    if quantity < reorder_point:
        return "high"
    if quantity < reorder_point * 1.15:
        return "medium"
    return "low"


def _snapshot_created_at(snapshot_date: date) -> datetime:
    """Converts a snapshot date into a UTC timestamp for API payloads."""

    return datetime.combine(snapshot_date, time.min, tzinfo=timezone.utc)


async def _load_latest_inventory_rows(
    session: AsyncSession,
    region_id: UUID | None = None,
) -> list[LatestInventoryRow]:
    """Loads the latest inventory row for each product-region combination."""

    latest_inventory = _latest_inventory_subquery()
    statement = (
        select(
            latest_inventory.c.snapshot_id,
            latest_inventory.c.quantity,
            latest_inventory.c.snapshot_date,
            Product,
            Region,
        )
        .join(Product, latest_inventory.c.product_id == Product.id)
        .join(Region, latest_inventory.c.region_id == Region.id)
        .where(latest_inventory.c.snapshot_rank == 1)
        .order_by(latest_inventory.c.snapshot_date.desc(), Product.name.asc(), Region.name.asc())
    )
    if region_id is not None:
        statement = statement.where(latest_inventory.c.region_id == region_id)

    rows = (await session.execute(statement)).all()
    return [
        LatestInventoryRow(
            snapshot_id=snapshot_id,
            quantity=quantity,
            snapshot_date=snapshot_date,
            product=product,
            region=region,
        )
        for snapshot_id, quantity, snapshot_date, product, region in rows
    ]


async def _load_latest_inventory_row(
    session: AsyncSession,
    *,
    product_id: UUID,
    region_id: UUID,
) -> LatestInventoryRow | None:
    """Loads the latest inventory row for a specific product-region pair."""

    statement = (
        select(InventorySnapshot, Product, Region)
        .join(Product, InventorySnapshot.product_id == Product.id)
        .join(Region, InventorySnapshot.region_id == Region.id)
        .where(
            InventorySnapshot.product_id == product_id,
            InventorySnapshot.region_id == region_id,
        )
        .order_by(InventorySnapshot.snapshot_date.desc(), InventorySnapshot.id.desc())
        .limit(1)
    )
    row = (await session.execute(statement)).first()
    if row is None:
        return None

    snapshot, product, region = row
    return LatestInventoryRow(
        snapshot_id=snapshot.id,
        quantity=snapshot.quantity,
        snapshot_date=snapshot.snapshot_date,
        product=product,
        region=region,
    )


async def _build_region_filtered_supplier_statement(region_id: UUID):
    """Builds a product filter for shipment aggregations scoped to a region."""

    latest_inventory = _latest_inventory_subquery()
    return (
        select(latest_inventory.c.product_id)
        .where(
            latest_inventory.c.snapshot_rank == 1,
            latest_inventory.c.region_id == region_id,
        )
        .distinct()
        .subquery()
    )


async def get_inventory_context(
    session: AsyncSession,
    *,
    product_id: UUID,
    region_id: UUID,
) -> LatestInventoryRow:
    """Returns the latest inventory context for a product-region pair."""

    context = await _load_latest_inventory_row(session, product_id=product_id, region_id=region_id)
    if context is None:
        raise LookupError("Inventory context was not found for the requested product and region.")
    return context


async def build_analytics_kpis(
    session: AsyncSession,
    *,
    region_id: UUID | None = None,
) -> list[KPI]:
    """Builds the analytics KPI collection from current inventory data."""

    rows = await _load_latest_inventory_rows(session, region_id=region_id)
    total_inventory_units = sum(row.quantity for row in rows)
    at_risk_positions = sum(1 for row in rows if row.quantity < (row.product.reorder_point or 0))
    tracked_products = len({row.product.id for row in rows})
    average_units_per_position = round(total_inventory_units / len(rows), 1) if rows else 0.0

    return [
        KPI(label="Inventory Units", value=total_inventory_units, change_note="Latest on-hand quantity across tracked positions."),
        KPI(label="At-Risk Positions", value=at_risk_positions, change_note="Latest snapshots below each product reorder threshold."),
        KPI(label="Tracked Products", value=tracked_products, change_note="Products represented in the latest inventory positions."),
        KPI(label="Avg Units / Position", value=average_units_per_position, change_note="Average latest quantity across active positions.", unit="units"),
    ]


async def build_demand_series(
    session: AsyncSession,
    *,
    region_id: UUID | None = None,
    lookback_days: int = 30,
) -> list[DemandPoint]:
    """Builds a compact demand trend series from recent daily sales."""

    start_date = date.today() - timedelta(days=lookback_days)
    statement = (
        select(DailySale.sale_date, func.sum(DailySale.units_sold).label("demand_units"))
        .where(DailySale.sale_date >= start_date)
        .group_by(DailySale.sale_date)
        .order_by(DailySale.sale_date.desc())
        .limit(6)
    )
    if region_id is not None:
        statement = statement.where(DailySale.region_id == region_id)

    rows = list(reversed((await session.execute(statement)).all()))
    return [
        DemandPoint(label=sale_date.strftime("%b %d"), demand_units=int(demand_units or 0))
        for sale_date, demand_units in rows
    ]


async def build_supplier_performance(
    session: AsyncSession,
    *,
    region_id: UUID | None = None,
) -> list[SupplierPerformanceItem]:
    """Builds shipment-truthful supplier performance metrics."""

    on_time_case = case(
        (
            and_(
                SupplierShipment.status == "delivered",
                SupplierShipment.actual_date.is_not(None),
                SupplierShipment.expected_date.is_not(None),
                SupplierShipment.actual_date <= SupplierShipment.expected_date,
            ),
            1,
        ),
        else_=0,
    )
    statement = select(
        SupplierShipment.supplier_name,
        func.count(SupplierShipment.id).label("shipment_count"),
        func.sum(case((SupplierShipment.status == "delivered", 1), else_=0)).label("delivered_count"),
        func.sum(case((SupplierShipment.status == "delayed", 1), else_=0)).label("delayed_count"),
        func.sum(case((SupplierShipment.status == "in_transit", 1), else_=0)).label("in_transit_count"),
        func.sum(on_time_case).label("on_time_delivered_count"),
    ).where(SupplierShipment.supplier_name.is_not(None))

    if region_id is not None:
        region_products = await _build_region_filtered_supplier_statement(region_id)
        statement = statement.join(region_products, SupplierShipment.product_id == region_products.c.product_id)

    statement = statement.group_by(SupplierShipment.supplier_name).order_by(SupplierShipment.supplier_name.asc())
    rows = (await session.execute(statement)).all()

    items: list[SupplierPerformanceItem] = []
    for supplier_name, shipment_count, delivered_count, delayed_count, in_transit_count, on_time_delivered_count in rows:
        delivered_count = int(delivered_count or 0)
        shipment_count = int(shipment_count or 0)
        items.append(
            SupplierPerformanceItem(
                supplier_name=str(supplier_name),
                shipment_count=shipment_count,
                delivered_count=delivered_count,
                delayed_count=int(delayed_count or 0),
                in_transit_count=int(in_transit_count or 0),
                on_time_rate_pct=round((float(on_time_delivered_count or 0) / max(delivered_count, 1)) * 100, 1) if delivered_count else 0.0,
            )
        )
    return items


async def list_alerts(
    session: AsyncSession,
    *,
    region_id: UUID | None = None,
    severity: str | None = None,
    limit: int = 6,
) -> list[AlertItem]:
    """Returns derived low-stock alerts ordered by recency."""

    rows = await _load_latest_inventory_rows(session, region_id=region_id)
    items: list[AlertItem] = []
    for row in rows:
        reorder_point = row.product.reorder_point or 0
        if reorder_point <= 0 or row.quantity >= reorder_point:
            continue

        derived_severity = _derive_risk_level(row.quantity, reorder_point)
        if severity is not None and derived_severity != severity:
            continue

        items.append(
            AlertItem(
                alert_id=row.snapshot_id,
                product_id=row.product.id,
                region_id=row.region.id,
                product_name=row.product.name,
                region_name=row.region.name,
                severity=derived_severity,
                message=f"{row.product.name} is below reorder threshold in {row.region.name}.",
                triggered_by="reorder_point_threshold",
                created_at=_snapshot_created_at(row.snapshot_date),
            )
        )

    return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]


async def list_inventory_positions(
    session: AsyncSession,
    *,
    region_id: UUID | None = None,
    below_reorder_only: bool = False,
    limit: int = 25,
) -> list[InventoryPositionItem]:
    """Returns latest inventory positions with derived risk labels."""

    rows = await _load_latest_inventory_rows(session, region_id=region_id)
    items: list[InventoryPositionItem] = []
    for row in rows:
        reorder_point = row.product.reorder_point
        if below_reorder_only and (reorder_point is None or row.quantity >= reorder_point):
            continue

        items.append(
            InventoryPositionItem(
                product_id=row.product.id,
                product_name=row.product.name,
                sku=row.product.sku,
                region_id=row.region.id,
                region_name=row.region.name,
                quantity=row.quantity,
                snapshot_date=row.snapshot_date,
                reorder_point=reorder_point,
                risk_level=_derive_risk_level(row.quantity, reorder_point),
            )
        )

    return items[:limit]


def _normalize_forecast_payload(payload: dict[str, object] | None) -> ForecastPayload:
    """Normalizes forecast JSON into the typed response schema."""

    return ForecastPayload.model_validate(
        payload
        or {
            "horizon_days": 7,
            "predictions": [],
            "summary": {
                "total_units": 0,
                "avg_daily_units": 0.0,
                "stockout_risk_pct": 0.0,
                "recommended_reorder_units": 0,
            },
        }
    )


def _normalize_shap_payload(payload: dict[str, object] | None) -> ForecastExplainabilityPayload:
    """Normalizes explanation JSON into the typed response schema."""

    return ForecastExplainabilityPayload.model_validate(
        payload
        or {
            "method": "feature_importance_proxy",
            "top_features": [],
        }
    )


def _to_forecast_response(record: ForecastRun, product: Product, region: Region) -> ForecastRecordResponse:
    """Maps ORM objects into the forecast response schema."""

    return ForecastRecordResponse(
        forecast_id=record.id,
        product_id=product.id,
        region_id=region.id,
        product_name=product.name,
        region_name=region.name,
        run_at=record.run_at or datetime.now(timezone.utc),
        forecast_json=_normalize_forecast_payload(record.forecast_json),
        shap_json=_normalize_shap_payload(record.shap_json),
    )


async def save_forecast_run(
    session: AsyncSession,
    *,
    product: Product,
    region: Region,
    forecast_json: dict[str, object],
    shap_json: dict[str, object],
) -> ForecastRecordResponse:
    """Persists a generated forecast and returns the response schema."""

    record = ForecastRun(
        product_id=product.id,
        region_id=region.id,
        forecast_json=forecast_json,
        shap_json=shap_json,
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
        .order_by(ForecastRun.run_at.desc(), ForecastRun.id.desc())
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
        .order_by(ForecastRun.run_at.desc(), ForecastRun.id.desc())
    )
    rows = (await session.execute(statement)).all()
    return [_to_forecast_response(record, product, region) for record, product, region in rows]


async def _get_snapshot_for_date(
    session: AsyncSession,
    *,
    product_id: UUID,
    region_id: UUID,
    snapshot_date: date,
) -> InventorySnapshot | None:
    """Returns the snapshot row for a specific product-region-date if it exists."""

    statement = select(InventorySnapshot).where(
        InventorySnapshot.product_id == product_id,
        InventorySnapshot.region_id == region_id,
        InventorySnapshot.snapshot_date == snapshot_date,
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def rebalance_inventory(
    session: AsyncSession,
    request: InventoryRebalanceRequest,
) -> InventoryRebalanceResponse:
    """Creates or updates today's inventory snapshots for the source and target regions."""

    product = await session.get(Product, request.product_id)
    source_region = await session.get(Region, request.source_region_id)
    target_region = await session.get(Region, request.target_region_id)
    if product is None or source_region is None or target_region is None:
        raise LookupError("The requested product or region was not found.")

    source_context = await _load_latest_inventory_row(
        session,
        product_id=request.product_id,
        region_id=request.source_region_id,
    )
    if source_context is None:
        raise LookupError("Inventory context was not found for the requested product and region.")

    target_context = await _load_latest_inventory_row(
        session,
        product_id=request.product_id,
        region_id=request.target_region_id,
    )

    if request.quantity_units > source_context.quantity:
        raise ValueError("Requested transfer exceeds available source inventory.")

    snapshot_date = date.today()
    source_today = await _get_snapshot_for_date(
        session,
        product_id=request.product_id,
        region_id=request.source_region_id,
        snapshot_date=snapshot_date,
    )
    target_today = await _get_snapshot_for_date(
        session,
        product_id=request.product_id,
        region_id=request.target_region_id,
        snapshot_date=snapshot_date,
    )

    if source_today is None:
        source_today = InventorySnapshot(
            product_id=request.product_id,
            region_id=request.source_region_id,
            quantity=source_context.quantity,
            snapshot_date=snapshot_date,
        )
        session.add(source_today)
    if target_today is None:
        target_today = InventorySnapshot(
            product_id=request.product_id,
            region_id=request.target_region_id,
            quantity=target_context.quantity if target_context is not None else 0,
            snapshot_date=snapshot_date,
        )
        session.add(target_today)

    source_today.quantity -= request.quantity_units
    target_today.quantity += request.quantity_units

    await session.commit()

    return InventoryRebalanceResponse(
        generated_at=datetime.now(timezone.utc),
        product_id=product.id,
        source_region_id=request.source_region_id,
        target_region_id=request.target_region_id,
        quantity_units=request.quantity_units,
        status="completed",
    )
