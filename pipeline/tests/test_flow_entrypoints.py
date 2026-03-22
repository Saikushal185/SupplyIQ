"""Regression tests for pipeline CLI entrypoints."""

import unittest
from unittest.mock import MagicMock, patch

from pipeline.flows.alert_flow import run_alert_cli
from pipeline.flows.ingestion_flow import run_ingestion_cli


class PipelineCliEntrypointTests(unittest.TestCase):
    """Ensures docker-facing entrypoints avoid Prefect engine startup."""

    @patch("pipeline.flows.ingestion_flow.load_supply_data")
    @patch("pipeline.flows.ingestion_flow.transform_supply_data")
    @patch("pipeline.flows.ingestion_flow.extract_seed_supply_data")
    def test_run_ingestion_cli_uses_task_functions(
        self,
        mock_extract: MagicMock,
        mock_transform: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Calls task `.fn` functions so CLI execution stays outside Prefect orchestration."""

        mock_extract.fn.return_value = {"inventory": []}
        mock_transform.fn.return_value = {"inventory": [], "alerts": []}
        mock_load.fn.return_value = {"inventory": 0, "alerts": 0}

        result = run_ingestion_cli()

        mock_extract.fn.assert_called_once_with()
        mock_transform.fn.assert_called_once_with({"inventory": []})
        mock_load.fn.assert_called_once_with({"inventory": [], "alerts": []})
        self.assertEqual(result, {"inventory": 0, "alerts": 0})

    @patch("pipeline.flows.alert_flow.refresh_alert_cache")
    def test_run_alert_cli_uses_direct_refresh(self, mock_refresh_alert_cache: MagicMock) -> None:
        """Executes the cache refresh helper directly for CLI runs."""

        mock_refresh_alert_cache.return_value = {
            "generated_at": "2026-03-22T00:00:00+00:00",
            "open_alert_count": 0,
            "critical_alert_count": 0,
        }

        result = run_alert_cli()

        mock_refresh_alert_cache.assert_called_once_with()
        self.assertEqual(result["open_alert_count"], 0)
