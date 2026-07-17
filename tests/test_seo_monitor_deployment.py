from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from seo_monitor.checks import deployment
from seo_monitor.storage import Store


class DeploymentCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "index.html").write_text("expected", encoding="utf-8")
        self.store = Store(f"sqlite:///{self.root / 'monitor.db'}")
        self.store.initialize()
        self.config = {
            "thresholds": {"health_timeout_seconds": 5},
            "deployment": {
                "probes": [{
                    "name": "Home",
                    "url": "https://example.com/",
                    "source_file": "index.html",
                    "severity": "P1",
                }],
            },
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def snapshot(content_hash: str) -> dict:
        return {
            "url": "https://example.com/",
            "status_code": 200,
            "final_url": "https://example.com/",
            "elapsed_ms": 100,
            "content_hash": content_hash,
            "error": None,
        }

    def run_check(self, content_hash: str):
        run_id = self.store.start_job("deployment")
        with patch.object(deployment, "ROOT", self.root):
            with patch.object(deployment, "inspect_remote", return_value=self.snapshot(content_hash)):
                result = deployment.run(self.config, self.store, run_id)
        self.store.save_result(run_id, result)
        return result

    def test_matching_public_file_is_healthy(self) -> None:
        expected = deployment.expected_hash("index.html", self.root)
        result = self.run_check(expected)
        self.assertEqual(result.alerts, [])
        self.assertEqual(result.summary["current_matches"], 1)

    def test_first_mismatch_waits_for_confirmation(self) -> None:
        result = self.run_check("stale")
        self.assertEqual(result.alerts, [])
        self.assertEqual(result.summary["mismatches"], 1)
        self.assertEqual(result.summary["confirmed_mismatches"], 0)

    def test_second_consecutive_mismatch_alerts(self) -> None:
        self.run_check("stale")
        result = self.run_check("stale")
        self.assertEqual(len(result.alerts), 1)
        self.assertEqual(result.alerts[0].severity, "P1")
        self.assertIn("dos comprobaciones consecutivas", result.alerts[0].message)

    def test_new_expected_version_restarts_confirmation(self) -> None:
        self.run_check("stale")
        (self.root / "index.html").write_text("new expected", encoding="utf-8")
        result = self.run_check("still stale")
        self.assertEqual(result.alerts, [])
        self.assertEqual(result.summary["confirmed_mismatches"], 0)

    def test_two_unavailable_responses_alert(self) -> None:
        unavailable = self.snapshot("")
        unavailable.update({"status_code": 404, "content_hash": None})
        run_id = self.store.start_job("deployment")
        with patch.object(deployment, "ROOT", self.root):
            with patch.object(deployment, "inspect_remote", return_value=unavailable):
                first = deployment.run(self.config, self.store, run_id)
        self.store.save_result(run_id, first)

        run_id = self.store.start_job("deployment")
        with patch.object(deployment, "ROOT", self.root):
            with patch.object(deployment, "inspect_remote", return_value=unavailable):
                second = deployment.run(self.config, self.store, run_id)
        self.assertEqual(len(second.alerts), 1)
        self.assertIn("no disponible", second.alerts[0].title.lower())


if __name__ == "__main__":
    unittest.main()
