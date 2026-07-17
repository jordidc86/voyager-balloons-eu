from __future__ import annotations

import unittest

from seo_monitor.config import Settings, load_config, load_keywords
from seo_monitor.runner import JOBS


class ConfigTests(unittest.TestCase):
    def test_production_config_has_required_scope(self) -> None:
        settings = Settings.from_env()
        config = load_config(settings)
        keywords = load_keywords(settings)
        self.assertGreaterEqual(len(config["strategic_pages"]), 10)
        self.assertGreaterEqual(len(config["competitors"]), 5)
        self.assertGreaterEqual(len(config["local_visibility"]["checks"]), 5)
        self.assertGreaterEqual(len(config["ai_visibility"]["providers"]), 3)
        self.assertGreaterEqual(len(config["ai_visibility"]["prompts"]), 7)
        self.assertEqual(config["local_visibility"]["cid"], "3510492992662249273")
        self.assertGreater(config["thresholds"]["dataforseo_monthly_budget_usd"], 0)
        self.assertGreater(config["thresholds"]["dataforseo_run_budget_usd"], 0)
        self.assertLessEqual(
            config["thresholds"]["dataforseo_run_budget_usd"],
            config["thresholds"]["dataforseo_monthly_budget_usd"],
        )
        self.assertGreaterEqual(len(keywords), 25)
        self.assertEqual({row["language_code"] for row in keywords}, {"es", "en", "pt"})
        self.assertTrue(all(row["priority"] in {"P0", "P1", "P2", "P3"} for row in keywords))
        self.assertEqual(set(config["schedules_seconds"]), set(JOBS) | {"digest"})


if __name__ == "__main__":
    unittest.main()
