from __future__ import annotations

import asyncio
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from pipeline.flows import alert_flow
from pipeline.tasks import extract, load, transform


class _FakeRedis:
    def __init__(self, keys: list[str] | None = None) -> None:
        self.keys = keys or []
        self.deleted: list[str] = []
        self.values: dict[str, str] = {}
        self.setex_calls: list[tuple[str, int, str]] = []

    def scan_iter(self, match: str | None = None):
        if match is None:
            yield from self.keys
            return
        prefix = match.rstrip("*")
        for key in self.keys:
            if key.startswith(prefix):
                yield key

    def delete(self, *keys: str) -> int:
        self.deleted.extend(keys)
        return len(keys)

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.values[key] = value
        self.setex_calls.append((key, ttl_seconds, value))
        return True


class PipelineIngestionTests(unittest.TestCase):
    def test_prefect_yaml_declares_daily_2am_utc_schedule(self) -> None:
        prefect_yaml = Path("pipeline/prefect.yaml").read_text(encoding="utf-8")

        self.assertIn("cron: 0 2 * * *", prefect_yaml)
        self.assertIn("timezone: UTC", prefect_yaml)

    def test_seasonality_and_time_of_day_factors_follow_requested_shape(self) -> None:
        self.assertGreater(
            extract.seasonal_multiplier("electronics", 11),
            extract.seasonal_multiplier("electronics", 6),
        )
        self.assertAlmostEqual(
            extract.seasonal_multiplier("food", 1),
            extract.seasonal_multiplier("food", 7),
        )
        self.assertGreater(
            extract.time_of_day_traffic_factor(datetime(2026, 3, 31, 17, 0, tzinfo=UTC)),
            extract.time_of_day_traffic_factor(datetime(2026, 3, 31, 2, 0, tzinfo=UTC)),
        )

    def test_build_live_daily_sales_rows_uses_weather_lookup_and_scaled_traffic(self) -> None:
        product_id = uuid4()
        region_id = uuid4()

        class _FakeRng:
            def normal(self, mean: float, std_dev: float) -> float:
                self.normal_args = (mean, std_dev)
                return 0.0

            def uniform(self, minimum: float, maximum: float) -> float:
                self.uniform_args = (minimum, maximum)
                return 0.5

        run_at = datetime(2026, 11, 15, 14, 0, tzinfo=UTC)
        rng = _FakeRng()
        rows = extract.build_live_daily_sales_rows(
            products=[
                {
                    "product_id": product_id,
                    "sku": "ELEC-100",
                    "category": "electronics",
                    "base_demand": 40,
                }
            ],
            regions=[
                {
                    "region_id": region_id,
                    "name": "North",
                    "city": "Chicago",
                }
            ],
            weather_by_region={str(region_id): 18.5},
            run_at=run_at,
            rng=rng,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_id"], product_id)
        self.assertEqual(rows[0]["region_id"], region_id)
        self.assertEqual(rows[0]["weather_temp"], 18.5)
        self.assertGreater(rows[0]["units_sold"], 40)
        self.assertAlmostEqual(
            rows[0]["traffic_index"],
            round(0.5 * extract.time_of_day_traffic_factor(run_at), 4),
        )

    def test_transform_supply_data_rejects_invalid_sales_and_flags_reorder_risk(self) -> None:
        product_id = uuid4()
        region_id = uuid4()

        transformed = transform.transform_supply_data.fn(
            {
                "products": [
                    {
                        "product_id": product_id,
                        "sku": "ELEC-100",
                        "unit_cost": 10.0,
                        "reorder_point": 20,
                    }
                ],
                "regions": [
                    {
                        "region_id": region_id,
                        "name": "North",
                    }
                ],
                "daily_sales": [
                    {
                        "product_id": product_id,
                        "region_id": region_id,
                        "sale_date": date(2026, 3, 31),
                        "units_sold": 5,
                        "weather_temp": 21.5,
                        "traffic_index": 0.44,
                    },
                    {
                        "product_id": None,
                        "region_id": region_id,
                        "sale_date": date(2026, 3, 31),
                        "units_sold": 4,
                        "weather_temp": 21.5,
                        "traffic_index": 0.44,
                    },
                    {
                        "product_id": product_id,
                        "region_id": region_id,
                        "sale_date": date(2026, 3, 31),
                        "units_sold": -2,
                        "weather_temp": 21.5,
                        "traffic_index": 0.44,
                    },
                ],
                "inventory_snapshots": [
                    {
                        "product_id": product_id,
                        "region_id": region_id,
                        "snapshot_date": date(2026, 3, 31),
                        "opening_quantity": 18,
                    }
                ],
            }
        )

        self.assertEqual(len(transformed["daily_sales"]), 1)
        self.assertEqual(transformed["daily_sales"][0]["revenue"], 50.0)
        self.assertEqual(len(transformed["rejected_daily_sales"]), 2)
        self.assertEqual(transformed["inventory_snapshots"][0]["projected_quantity"], 13)
        self.assertTrue(transformed["inventory_snapshots"][0]["below_reorder"])

    def test_build_inventory_rows_for_load_subtracts_units_from_opening_quantity(self) -> None:
        rows = load.build_inventory_rows_for_load(
            [
                {
                    "product_id": uuid4(),
                    "region_id": uuid4(),
                    "snapshot_date": date(2026, 3, 31),
                    "opening_quantity": 25,
                    "units_sold": 7,
                    "below_reorder": False,
                }
            ]
        )

        self.assertEqual(rows[0]["quantity"], 18)

    def test_invalidate_analytics_cache_deletes_matching_keys(self) -> None:
        redis_client = _FakeRedis(
            keys=[
                "analytics:sales:1",
                "supplyiq:analytics:2",
                "forecast:latest:3",
            ]
        )

        deleted = load.invalidate_analytics_cache(redis_client)

        self.assertEqual(deleted, 2)
        self.assertEqual(
            redis_client.deleted,
            ["analytics:sales:1", "supplyiq:analytics:2"],
        )

    def test_alert_rate_limit_sends_once_per_product_per_day(self) -> None:
        redis_client = _FakeRedis()
        product_id = uuid4()
        now = datetime(2026, 3, 31, 2, 0, tzinfo=UTC)

        first = alert_flow.should_send_inventory_alert(
            redis_client,
            product_id=product_id,
            now=now,
        )
        second = alert_flow.should_send_inventory_alert(
            redis_client,
            product_id=product_id,
            now=now,
        )

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(redis_client.setex_calls[0][1], 86400)

    def test_dispatch_inventory_alerts_skips_rate_limited_products(self) -> None:
        redis_client = _FakeRedis()
        sent: list[tuple[str, str]] = []

        async def _email_sender(*, product_name: str, region_name: str, recipient_email: str, quantity: int, reorder_point: int) -> bool:
            sent.append((product_name, recipient_email))
            return True

        rows = [
            {
                "product_id": uuid4(),
                "product_name": "Scanner",
                "region_name": "North",
                "quantity": 10,
                "reorder_point": 20,
            }
        ]

        first_result = asyncio.run(
            alert_flow.dispatch_inventory_alerts(
                rows,
                redis_client=redis_client,
                recipient_email="alerts@supplyiq.test",
                email_sender=_email_sender,
                now=datetime(2026, 3, 31, 2, 0, tzinfo=UTC),
            )
        )
        second_result = asyncio.run(
            alert_flow.dispatch_inventory_alerts(
                rows,
                redis_client=redis_client,
                recipient_email="alerts@supplyiq.test",
                email_sender=_email_sender,
                now=datetime(2026, 3, 31, 3, 0, tzinfo=UTC),
            )
        )

        self.assertEqual(first_result["sent"], 1)
        self.assertEqual(second_result["sent"], 0)
        self.assertEqual(first_result["rate_limited"], 0)
        self.assertEqual(second_result["rate_limited"], 1)
        self.assertEqual(sent, [("Scanner", "alerts@supplyiq.test")])


if __name__ == "__main__":
    unittest.main()
