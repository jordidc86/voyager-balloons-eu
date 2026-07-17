from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from seo_monitor.checks.ai_visibility import _is_due as ai_is_due
from seo_monitor.checks.rank import _depth_for


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


if __name__ == "__main__":
    unittest.main()
