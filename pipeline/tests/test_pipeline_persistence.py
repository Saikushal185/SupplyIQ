"""Regression tests for pipeline persistence helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from pipeline.tasks import load


class PipelinePersistenceTests(unittest.TestCase):
    """Validates pipeline DB URL normalization for direct PostgreSQL writes."""

    def test_build_postgres_dsn_removes_sqlalchemy_driver_suffix(self) -> None:
        """Strips the SQLAlchemy driver so direct DB clients can connect."""

        self.assertEqual(
            load.build_postgres_dsn("postgresql+psycopg://supplyiq:secret@postgres:5432/supplyiq"),
            "postgresql://supplyiq:secret@postgres:5432/supplyiq",
        )

    def test_insert_alert_writes_explicit_acknowledged_false(self) -> None:
        """Ensures raw alert inserts preserve the ORM's previous default."""

        cursor = MagicMock()

        load._insert_alert(
            cursor,
            product_id="product-1",
            region_id="region-1",
            payload={
                "severity": "high",
                "message": "Below reorder point.",
                "triggered_by": "pipeline_reorder_monitor",
            },
        )

        statement, params = cursor.execute.call_args.args
        self.assertIn("acknowledged", statement.lower())
        self.assertEqual(params[-1], False)
