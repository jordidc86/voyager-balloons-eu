from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from seo_monitor.checks.ai_visibility import _is_due as ai_is_due
from seo_monitor.checks.rank import _depth_for, _drop_assessment, run as run_rank


class SeoMonitorCadenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc)
        self.thresholds = {
            "rank_critical_depth": 20,
            "rank_secondary_depth": 100,
            "rank_secondary_interval_days": 7,
        }

    def previous(self, days_ago: int, naive: bool = False):
        observed_at = self.now - timedelta(days=days_ago)
        if naive:
            observed_at = observed_at.replace(tzinfo=None)
        return SimpleNamespace(observed_at=observed_at)

    def test_critical_rank_is_checked_daily_at_shallow_depth(self):
        row = {"priority": "P0"}
        self.assertEqual(_depth_for(row, self.previous(0), self.thresholds), 20)

    def test_new_secondary_rank_gets_full_baseline(self):
        row = {"priority": "P1"}
        self.assertEqual(_depth_for(row, None, self.thresholds), 100)

    def test_recent_secondary_rank_is_deferred(self):
        row = {"priority": "P1"}
        self.assertIsNone(_depth_for(row, self.previous(0), self.thresholds))

    def test_old_secondary_rank_gets_full_refresh(self):
        row = {"priority": "P1"}
        self.assertEqual(_depth_for(row, self.previous(8), self.thresholds), 100)

    def test_ai_secondary_observation_uses_28_day_cadence(self):
        self.assertFalse(ai_is_due(self.previous(27), 28, now=self.now))
        self.assertTrue(ai_is_due(self.previous(29), 28, now=self.now))

    def test_naive_stored_timestamp_is_treated_as_utc(self):
        self.assertTrue(ai_is_due(self.previous(29, naive=True), 28, now=self.now))

    def test_rank_drop_uses_stable_median_instead_of_last_fluctuation(self):
        history = [
            SimpleNamespace(position=24),
            SimpleNamespace(position=33),
            SimpleNamespace(position=33),
        ]
        self.assertIsNone(_drop_assessment(history, 33, 100, 3))

    def test_rank_drop_becomes_confirmed_after_two_bad_observations(self):
        history = [
            SimpleNamespace(position=20),
            SimpleNamespace(position=10),
            SimpleNamespace(position=10),
        ]
        drop = _drop_assessment(history, 20, 100, 3)
        self.assertIsNotNone(drop)
        self.assertTrue(drop["confirmed"])
        self.assertEqual(drop["baseline"], 10)

    @patch("seo_monitor.checks.rank._search", return_value=({"items": []}, 0.01))
    @patch("seo_monitor.checks.rank.load_keywords")
    def test_rank_run_passes_thresholds_to_cadence_logic(self, load_keywords, search):
        load_keywords.return_value = [{
            "keyword": "vuelo en globo segovia",
            "location_name": "Madrid,Community of Madrid,Spain",
            "language_code": "es",
            "device": "mobile",
            "priority": "P0",
            "cluster": "segovia",
            "target_url": "https://www.voyagerballoons.eu/vuelo-en-globo-segovia",
        }]
        store = Mock()
        store.previous_keyword_ranking.return_value = None
        store.keyword_ranking_history.return_value = []
        settings = SimpleNamespace(dataforseo_login="login", dataforseo_password="password")
        config = {
            "target_domains": ["www.voyagerballoons.eu"],
            "thresholds": {
                **self.thresholds,
                "rank_drop_positions": 3,
                "dataforseo_run_budget_usd": 1,
            },
            "_runtime": {"dataforseo_budget_remaining_usd": 1},
        }

        result = run_rank(config, store, 1, settings)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.summary["keywords_checked"], 1)
        self.assertEqual(result.summary["provider_cost_usd"], 0.01)
        search.assert_called_once()


if __name__ == "__main__":
    unittest.main()
