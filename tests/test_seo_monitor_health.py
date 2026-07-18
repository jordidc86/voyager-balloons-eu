from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from seo_monitor.checks import http_health
from seo_monitor.storage import Store


class HealthCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(f"sqlite:///{Path(self.tmp.name) / 'monitor.db'}")
        self.store.initialize()
        self.config = {
            "thresholds": {
                "health_timeout_seconds": 5,
                "slow_page_ms": 1000,
                "slow_page_confirmations": 3,
            },
            "strategic_pages": [{
                "name": "Landing",
                "url": "https://example.com/landing/",
                "canonical": "https://example.com/landing",
                "required_text": ["215"],
                "severity": "P0",
            }],
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def snapshot(self, **overrides):
        payload = {
            "url": "https://example.com/landing/",
            "status_code": 200,
            "final_url": "https://example.com/landing/",
            "redirects": 0,
            "elapsed_ms": 1500,
            "content_type": "text/html",
            "title": "Landing",
            "canonical": "https://example.com/landing/",
            "robots": "index,follow",
            "h1_count": 1,
            "visible_text": "Price 215 EUR",
            "content_hash": "abc",
            "error": None,
        }
        payload.update(overrides)
        return payload

    def test_first_slow_sample_does_not_alert(self) -> None:
        run_id = self.store.start_job("health")
        with patch.object(http_health, "inspect_page", return_value=self.snapshot()):
            result = http_health.run(self.config, self.store, run_id)
        self.assertEqual(result.alerts, [])

    def test_second_slow_sample_does_not_alert(self) -> None:
        first_run = self.store.start_job("health")
        with patch.object(http_health, "inspect_page", return_value=self.snapshot()):
            first = http_health.run(self.config, self.store, first_run)
        self.store.save_result(first_run, first)

        second_run = self.store.start_job("health")
        with patch.object(http_health, "inspect_page", return_value=self.snapshot(elapsed_ms=1400)):
            second = http_health.run(self.config, self.store, second_run)
        self.assertEqual(second.alerts, [])

    def test_third_slow_sample_alerts(self) -> None:
        for elapsed_ms in (1500, 1400):
            run_id = self.store.start_job("health")
            with patch.object(http_health, "inspect_page", return_value=self.snapshot(elapsed_ms=elapsed_ms)):
                result = http_health.run(self.config, self.store, run_id)
            self.store.save_result(run_id, result)

        third_run = self.store.start_job("health")
        with patch.object(http_health, "inspect_page", return_value=self.snapshot(elapsed_ms=1300)):
            third = http_health.run(self.config, self.store, third_run)

        self.assertEqual(len(third.alerts), 1)
        self.assertTrue(third.alerts[0].dedupe_key.startswith("health:slow:"))
        self.assertEqual(third.alerts[0].metadata["slow_streak"], 3)

    def test_noindex_and_missing_price_are_critical(self) -> None:
        run_id = self.store.start_job("health")
        with patch.object(http_health, "inspect_page", return_value=self.snapshot(robots="noindex", visible_text="No price")):
            result = http_health.run(self.config, self.store, run_id)
        keys = {alert.dedupe_key for alert in result.alerts}
        self.assertTrue(any(":noindex:" in key for key in keys))
        self.assertTrue(any(":required-text:" in key for key in keys))


if __name__ == "__main__":
    unittest.main()
