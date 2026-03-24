"""SQLAlchemy ORM models for the exact SupplyIQ persisted schema."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, desc, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM tables."""


class Product(Base):
    """Represents a catalog product."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    unit_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    reorder_point: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(), server_default=func.now())

    inventory_snapshots: Mapped[list["InventorySnapshot"]] = relationship(back_populates="product")
    daily_sales: Mapped[list["DailySale"]] = relationship(back_populates="product")
    supplier_shipments: Mapped[list["SupplierShipment"]] = relationship(back_populates="product")
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(back_populates="product")


class Region(Base):
    """Represents an operating region."""

    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str | None] = mapped_column(String(50))

    inventory_snapshots: Mapped[list["InventorySnapshot"]] = relationship(back_populates="region")
    daily_sales: Mapped[list["DailySale"]] = relationship(back_populates="region")
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(back_populates="region")


class InventorySnapshot(Base):
    """Represents inventory on a given date for a product-region pair."""

    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        UniqueConstraint("product_id", "region_id", "snapshot_date", name="uq_inventory_snapshots_product_region_date"),
        Index("ix_inventory_snapshots_product_id_snapshot_date", "product_id", "snapshot_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    product: Mapped[Product | None] = relationship(back_populates="inventory_snapshots")
    region: Mapped[Region | None] = relationship(back_populates="inventory_snapshots")


class DailySale(Base):
    """Represents a single day's sales observation."""

    __tablename__ = "daily_sales"
    __table_args__ = (
        Index("ix_daily_sales_product_id_sale_date", "product_id", "sale_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"))
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[float | None] = mapped_column(Numeric(12, 2))
    weather_temp: Mapped[float | None] = mapped_column(Numeric(5, 2))
    traffic_index: Mapped[float | None] = mapped_column(Numeric(4, 2))

    product: Mapped[Product | None] = relationship(back_populates="daily_sales")
    region: Mapped[Region | None] = relationship(back_populates="daily_sales")


class SupplierShipment(Base):
    """Represents a supplier shipment for a product."""

    __tablename__ = "supplier_shipments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    supplier_name: Mapped[str | None] = mapped_column(String(200))
    expected_date: Mapped[date | None] = mapped_column(Date)
    actual_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(20))

    product: Mapped[Product | None] = relationship(back_populates="supplier_shipments")


class ForecastRun(Base):
    """Stores a generated forecast payload and explanation payload."""

    __tablename__ = "forecast_runs"
    __table_args__ = (
        Index("ix_forecast_runs_product_id_run_at_desc", "product_id", desc("run_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    run_at: Mapped[datetime | None] = mapped_column(DateTime(), server_default=func.now())
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"))
    forecast_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    shap_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)

    product: Mapped[Product | None] = relationship(back_populates="forecast_runs")
    region: Mapped[Region | None] = relationship(back_populates="forecast_runs")
