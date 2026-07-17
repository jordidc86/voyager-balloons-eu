from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from seo_monitor.config import Settings
from seo_monitor.runner import execute
from seo_monitor.storage import Store


class RunnerBudgetTests(unittest.TestCase):
    @patch("seo_monitor.runner.dataforseo_account_budget")
    def test_paid_job_skips_when_provider_daily_budget_is_reached(self, account_budget) -> None:
        account_budget.return_value = {
            "balance": 49.97,
            "day_limit_usd": 1.0,
            "day_spent_usd": 1.029,
            "day": "2026-07-17",
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            settings = replace(
                Settings.from_env(),
                dataforseo_login="login",
                dataforseo_password="password",
                dataforseo_enabled=True,
                dry_run=True,
            )

            result, _ = execute("rank", settings, store)

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.summary["reason"], "Presupuesto diario de DataForSEO alcanzado")
        self.assertEqual(result.summary["provider_day_limit_usd"], 1.0)


if __name__ == "__main__":
    unittest.main()
