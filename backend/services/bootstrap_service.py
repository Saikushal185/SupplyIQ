"""First-run bootstrap: seeds the database and trains ML models when missing."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func, select

from backend.ml.predict import XGB_ARTIFACT_PATH
from backend.models.db_models import DailySale
from backend.services.db_service import SessionLocal

logger = logging.getLogger(__name__)


async def needs_seed() -> bool:
    """Returns whether the daily_sales table is empty."""

    async with SessionLocal() as session:
        count = (await session.execute(select(func.count(DailySale.id)))).scalar_one()
    return int(count) == 0


def needs_train() -> bool:
    """Returns whether the global ML artifacts are missing."""

    return not XGB_ARTIFACT_PATH.exists()


def _run_seed() -> None:
    from infra.seed import seed_database

    counts = seed_database()
    logger.info("Bootstrap seeded database: %s", counts)


def _run_train() -> None:
    from backend.ml.train import persist_models

    artifacts = persist_models()
    logger.info("Bootstrap trained %s model artifacts.", len(artifacts))


async def run_auto_bootstrap() -> None:
    """Seeds and trains on first startup; both steps are idempotent and never block app startup on failure."""

    loop = asyncio.get_running_loop()

    seeded = False
    try:
        if await needs_seed():
            logger.info("Bootstrap: empty database detected, seeding two years of history...")
            await loop.run_in_executor(None, _run_seed)
            seeded = True
    except Exception:
        logger.exception("Bootstrap seeding failed; the API will start with an empty database.")

    try:
        if seeded or needs_train():
            logger.info("Bootstrap: training forecast models (this can take a few minutes on first run)...")
            await loop.run_in_executor(None, _run_train)
    except Exception:
        logger.exception("Bootstrap training failed; forecasts will return errors until train.py is run.")
