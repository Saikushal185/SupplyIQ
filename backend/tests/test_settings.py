"""Regression tests for backend settings parsing."""

import os
import unittest
from unittest.mock import patch

from backend.settings import Settings


class SettingsParsingTests(unittest.TestCase):
    """Covers environment parsing behavior for backend settings."""

    def test_cors_origins_accepts_single_origin_string(self) -> None:
        """Parses a plain origin string from the environment into a list."""

        with patch.dict(
            os.environ,
            {"BACKEND_CORS_ORIGINS": "http://localhost:3000"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.cors_origins, ["http://localhost:3000"])
