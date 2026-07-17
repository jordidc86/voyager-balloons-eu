from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from seo_monitor.storage import Store, normalize_database_url
from seo_monitor.types import AlertSpec, CheckResult


class StoreTests(unittest.TestCase):
    def test_normalizes_railway_postgres_urls_to_psycopg_v3(self):
        self.assertEqual(
            normalize_database_url("postgresql://user:pass@host:5432/db"),
            "postgresql+psycopg://user:pass@host:5432/db",
        )
        self.assertEqual(
            normalize_database_url("postgres://user:pass@host:5432/db"),
            "postgresql+psycopg://user:pass@host:5432/db",
        )
        self.assertEqual(
            normalize_database_url("sqlite:///tmp/monitor.db"),
            "sqlite:///tmp/monitor.db",
        )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(f"sqlite:///{Path(self.tmp.name) / 'monitor.db'}")
        self.store.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_alert_is_opened_deduplicated_and_resolved(self) -> None:
        alert = AlertSpec(
            dedupe_key="health:test",
            severity="P0",
            category="health",
            title="Test",
            message="Broken",
            action="Fix it",
        )
        first_run = self.store.start_job("health")
        changed = self.store.save_result(first_run, CheckResult(job_name="health", alerts=[alert]))
        self.assertEqual(len(changed), 1)
        self.assertEqual(len(self.store.open_alerts()), 1)

        second_run = self.store.start_job("health")
        changed = self.store.save_result(second_run, CheckResult(job_name="health", alerts=[alert]))
        self.assertEqual(changed, [])
        self.assertEqual(self.store.open_alerts()[0].occurrences, 2)

        third_run = self.store.start_job("health")
        changed = self.store.save_result(third_run, CheckResult(job_name="health"))
        self.assertEqual(len(changed), 1)
        self.assertEqual(self.store.open_alerts(), [])

    def test_metrics_and_snapshots_are_persisted(self) -> None:
        run_id = self.store.start_job("health")
        result = CheckResult(job_name="health")
        result.add_metric("response_ms", 123, dimensions={"url": "https://example.com"})
        self.store.add_page_snapshot(run_id, "health", {
            "url": "https://example.com",
            "status_code": 200,
            "final_url": "https://example.com",
            "elapsed_ms": 123,
            "title": "Example",
            "canonical": "https://example.com",
            "robots": "index,follow",
            "content_hash": "abc",
        })
        self.store.save_result(run_id, result)
        latest = self.store.latest_page_snapshot("health", "https://example.com")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(
            self.store.metric_sum_since("response_ms", datetime(2000, 1, 1, tzinfo=timezone.utc)),
            123,
        )

    def test_skipped_run_does_not_resolve_existing_alert(self) -> None:
        alert = AlertSpec(
            dedupe_key="rank:test",
            severity="P1",
            category="rank",
            title="Test rank",
            message="Dropped",
            action="Review",
        )
        first_run = self.store.start_job("rank")
        self.store.save_result(first_run, CheckResult(job_name="rank", alerts=[alert]))

        skipped_run = self.store.start_job("rank")
        self.store.save_result(skipped_run, CheckResult(job_name="rank", status="skipped"))

        self.assertEqual(len(self.store.open_alerts()), 1)
        self.assertEqual(self.store.open_alerts()[0].dedupe_key, "rank:test")

    def test_local_and_ai_observations_are_persisted(self) -> None:
        local_run = self.store.start_job("local_visibility")
        self.store.add_local_ranking(local_run, {
            "keyword": "vuelo en globo segovia",
            "language_code": "es",
            "location_label": "Segovia centro",
            "location_coordinate": "40.9429,-4.1088,13z",
            "position": 2,
            "title": "Voyager Balloons EU - Paseos en Globo",
            "cid": "3510492992662249273",
            "place_id": "test-place",
            "rating": 4.9,
            "reviews_count": 365,
        })
        self.store.save_result(local_run, CheckResult(job_name="local_visibility"))
        previous_local = self.store.previous_local_ranking("vuelo en globo segovia", "Segovia centro")
        self.assertIsNotNone(previous_local)
        self.assertEqual(previous_local.position, 2)
        self.assertEqual(
            len(self.store.local_ranking_history("vuelo en globo segovia", "Segovia centro")),
            1,
        )

        ai_run = self.store.start_job("ai_visibility")
        self.store.add_ai_visibility_observation(ai_run, {
            "prompt_id": "es-segovia-operadores",
            "prompt": "¿Qué empresa recomiendas?",
            "language_code": "es",
            "market": "Segovia",
            "provider": "chat_gpt",
            "model_name": "gpt-test",
            "voyager_mentioned": True,
            "voyager_cited": True,
            "competitor_mentions": [],
            "citations": [{"url": "https://www.voyagerballoons.eu/"}],
            "response_text": "Voyager Balloons",
        })
        self.store.save_result(ai_run, CheckResult(job_name="ai_visibility"))
        previous_ai = self.store.previous_ai_visibility("es-segovia-operadores", "chat_gpt")
        self.assertIsNotNone(previous_ai)
        self.assertEqual(previous_ai.voyager_mentioned, 1)
        self.assertEqual(previous_ai.voyager_cited, 1)


if __name__ == "__main__":
    unittest.main()
