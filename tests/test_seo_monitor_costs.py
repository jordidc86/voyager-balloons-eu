from __future__ import annotations

import unittest

from seo_monitor.costs import budget_available, dataforseo_run_budget


class CostControlTests(unittest.TestCase):
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
