"""SQLAlchemy ORM models for SupplyIQ."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM tables."""


class Supplier(Base):
    """Represents a supplier entity in the network."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    supplier_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    reliability_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")


class Region(Base):
    """Represents an operating region or distribution node."""

    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    region_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    market: Mapped[str] = mapped_column(String(80), nullable=False)
    risk_factor: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    inventory_snapshots: Mapped[list["InventorySnapshot"]] = relationship(back_populates="region")
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(back_populates="region")
    alerts: Mapped[list["InventoryAlert"]] = relationship(back_populates="region")


class Product(Base):
    """Represents a forecastable product."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False)
    base_daily_demand: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    supplier: Mapped[Supplier] = relationship(back_populates="products")
    inventory_snapshots: Mapped[list["InventorySnapshot"]] = relationship(back_populates="product")
    forecast_runs: Mapped[list["ForecastRun"]] = relationship(back_populates="product")
    alerts: Mapped[list["InventoryAlert"]] = relationship(back_populates="product")


class InventorySnapshot(Base):
    """Represents an inventory position at a given moment."""

    __tablename__ = "inventory_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inbound_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="inventory_snapshots")
    region: Mapped[Region] = relationship(back_populates="inventory_snapshots")


class ForecastRun(Base):
    """Stores a generated forecast result."""

    __tablename__ = "forecast_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_demand_units: Mapped[int] = mapped_column(Integer, nullable=False)
    lower_bound_units: Mapped[int] = mapped_column(Integer, nullable=False)
    upper_bound_units: Mapped[int] = mapped_column(Integer, nullable=False)
    stockout_probability_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    recommended_reorder_units: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="forecast_runs")
    region: Mapped[Region] = relationship(back_populates="forecast_runs")


class InventoryAlert(Base):
    """Stores inventory and supply disruption alerts."""

    __tablename__ = "inventory_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="alerts")
    region: Mapped[Region] = relationship(back_populates="alerts")
