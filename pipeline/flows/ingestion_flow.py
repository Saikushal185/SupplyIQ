"""Main data ingestion flow for SupplyIQ."""

from __future__ import annotations

from typing import Callable

from pipeline.tasks.extract import extract_seed_supply_data
from pipeline.tasks.load import load_supply_data
from pipeline.tasks.transform import transform_supply_data


def execute_ingestion_pipeline(
    extract_step: Callable[[], dict[str, list[dict[str, object]]]],
    transform_step: Callable[[dict[str, list[dict[str, object]]]], dict[str, list[dict[str, object]]]],
    load_step: Callable[[dict[str, list[dict[str, object]]]], dict[str, int]],
) -> dict[str, int]:
    """Runs ingestion with injectable steps for flow and CLI entrypoints."""

    raw_data = extract_step()
    transformed_data = transform_step(raw_data)
    return load_step(transformed_data)


def run_ingestion_flow() -> dict[str, int]:
    """Runs the end-to-end seed ingestion pipeline."""

    return execute_ingestion_pipeline(
        extract_seed_supply_data,
        transform_supply_data,
        load_supply_data,
    )


if __name__ == "__main__":
    run_ingestion_flow()
