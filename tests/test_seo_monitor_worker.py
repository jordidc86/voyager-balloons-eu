from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from seo_monitor.worker import _due, run_due_once


class WorkerTests(unittest.TestCase):
    def test_failed_jobs_retry_after_one_hour(self) -> None:
        run = SimpleNamespace(
            status="failed",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        self.assertTrue(_due(run, 604800))

    def test_skipped_jobs_retry_on_next_six_hour_cron(self) -> None:
        recent = SimpleNamespace(
            status="skipped",
            started_at=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        old = SimpleNamespace(
            status="skipped",
            started_at=datetime.now(timezone.utc) - timedelta(hours=7),
        )
        self.assertFalse(_due(recent, 604800))
        self.assertTrue(_due(old, 604800))

    @patch("seo_monitor.worker.ping_heartbeat")
    @patch("seo_monitor.worker.execute", side_effect=RuntimeError("boom"))
    @patch("seo_monitor.worker.send_digest", return_value="Informe")
    @patch("seo_monitor.worker.load_config")
    @patch("seo_monitor.worker.JOBS", {"health": object()})
    def test_failed_cycle_does_not_send_success_heartbeat(self, load_config, send_digest, execute, ping) -> None:
        load_config.return_value = {
            "schedules_seconds": {"health": 1, "digest": 1},
        }
        store = MagicMock()
        store.latest_run.return_value = None
        store.start_job.return_value = 1
        settings = SimpleNamespace(heartbeat_url="https://example.com/heartbeat", dry_run=True)

        with self.assertLogs("voyager-seo-monitor", level="WARNING"):
            summary = run_due_once(settings, store)

        self.assertGreater(summary["failed"], 0)
        ping.assert_not_called()


if __name__ == "__main__":
    unittest.main()
