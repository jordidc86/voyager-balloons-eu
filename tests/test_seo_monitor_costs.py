from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from seo_monitor.config import Settings
from seo_monitor.costs import budget_available, dataforseo_account_budget, dataforseo_run_budget


class CostControlTests(unittest.TestCase):
    @patch("seo_monitor.costs.requests.get")
    def test_provider_budget_is_parsed(self, get) -> None:
        response = Mock()
        response.json.return_value = {
            "tasks": [{
                "status_code": 20000,
                "result": [{
                    "money": {
                        "balance": 49.97,
                        "limits": {"day": {"total": 1}},
                        "statistics": {"day": {"total": 1.029, "value": "2026-07-17"}},
                    },
                }],
            }],
        }
        get.return_value = response

        budget = dataforseo_account_budget(Settings.from_env())

        self.assertEqual(budget["balance"], 49.97)
        self.assertEqual(budget["day_limit_usd"], 1)
        self.assertEqual(budget["day_spent_usd"], 1.029)
        response.raise_for_status.assert_called_once()

    def test_runtime_remaining_budget_overrides_normal_run_cap(self) -> None:
        config = {
            "thresholds": {"dataforseo_run_budget_usd": 5},
            "_runtime": {"dataforseo_budget_remaining_usd": 0.75},
        }
        self.assertEqual(dataforseo_run_budget(config), 0.75)
        self.assertTrue(budget_available(config, 0.74))
        self.assertFalse(budget_available(config, 0.75))

    def test_budget_never_becomes_negative(self) -> None:
        config = {"_runtime": {"dataforseo_budget_remaining_usd": -1}}
        self.assertEqual(dataforseo_run_budget(config), 0)
        self.assertFalse(budget_available(config, 0))


if __name__ == "__main__":
    unittest.main()
