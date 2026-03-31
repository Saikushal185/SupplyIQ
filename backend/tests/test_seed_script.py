from __future__ import annotations

import unittest
from datetime import date

from infra import seed


class SeedScriptTests(unittest.TestCase):
    def test_build_seed_dataset_generates_requested_catalog_and_two_year_history(self) -> None:
        dataset = seed.build_seed_dataset(
            end_date=date(2026, 3, 31),
            days=730,
        )

        self.assertEqual(len(dataset["products"]), 20)
        self.assertEqual(len(dataset["regions"]), 5)
        self.assertEqual(
            len(dataset["daily_sales"]),
            20 * 5 * 730,
        )
        self.assertEqual(
            sorted({product["category"] for product in dataset["products"]}),
            ["apparel", "electronics", "food", "household"],
        )

    def test_seed_dataset_bakes_in_requested_category_seasonality(self) -> None:
        dataset = seed.build_seed_dataset(
            end_date=date(2026, 3, 31),
            days=730,
        )

        electronics_holiday_units = sum(
            row["units_sold"]
            for row in dataset["daily_sales"]
            if row["category"] == "electronics" and row["sale_date"].month in {11, 12}
        )
        electronics_summer_units = sum(
            row["units_sold"]
            for row in dataset["daily_sales"]
            if row["category"] == "electronics" and row["sale_date"].month in {6, 7}
        )
        food_holiday_units = sum(
            row["units_sold"]
            for row in dataset["daily_sales"]
            if row["category"] == "food" and row["sale_date"].month in {11, 12}
        )
        food_summer_units = sum(
            row["units_sold"]
            for row in dataset["daily_sales"]
            if row["category"] == "food" and row["sale_date"].month in {6, 7}
        )

        self.assertGreater(electronics_holiday_units, electronics_summer_units)
        self.assertLess(
            abs(food_holiday_units - food_summer_units),
            electronics_holiday_units - electronics_summer_units,
        )


if __name__ == "__main__":
    unittest.main()
