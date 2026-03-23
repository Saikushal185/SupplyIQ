"""Database connection helpers for the SupplyIQ pipeline."""

from __future__ import annotations

import os


def get_pipeline_database_url() -> str:
    """Reads the pipeline database URL from the environment."""

    database_url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL")
    if not database_url:
        raise RuntimeError("PIPELINE_DATABASE_URL must be set for pipeline loading.")
    return database_url


def build_postgres_dsn(database_url: str) -> str:
    """Converts SQLAlchemy-style URLs into direct PostgreSQL DSNs."""

    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url
