from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

from seo_monitor.models import JobRun
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
        self.assertEqual(
            self.store.metric_history(
                "response_ms",
                "health",
                {"url": "https://example.com"},
            ),
            [123],
        )

    def test_snapshot_set_is_loaded_from_latest_successful_run(self) -> None:
        first_run = self.store.start_job("backlink_gap")
        self.store.add_page_snapshot(first_run, "backlink_profile", {
            "url": "https://example.com",
            "domain": "example.com",
            "present": True,
        })
        self.store.save_result(first_run, CheckResult(job_name="backlink_gap"))

        failed_run = self.store.start_job("backlink_gap")
        self.store.add_page_snapshot(failed_run, "backlink_profile", {
            "url": "https://ignored.example",
            "domain": "ignored.example",
            "present": True,
        })
        self.store.fail_job(failed_run, "provider failure")

        snapshots = self.store.page_snapshots_for_latest_success("backlink_profile", "backlink_gap")

        self.assertEqual([snapshot.url for snapshot in snapshots], ["https://example.com"])

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

    def test_stale_running_job_is_failed_and_can_be_retried(self) -> None:
        run_id = self.store.start_job("pagespeed")
        with self.store.sessions.begin() as session:
            session.get(JobRun, run_id).started_at = datetime.now(timezone.utc) - timedelta(hours=3)

        recovered = self.store.fail_stale_runs(datetime.now(timezone.utc) - timedelta(hours=2))
        latest = self.store.latest_run("pagespeed")

        self.assertEqual(recovered, 1)
        self.assertEqual(latest.status, "failed")
        self.assertIn("interrumpida", latest.error)

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

    def test_keyword_candidates_are_deduplicated_and_activated(self) -> None:
        run_id = self.store.start_job("gsc")
        payload = {
            "query": "  Balloon Ride Segovia Price ",
            "language_code": "en",
            "location_name": "Madrid Spain",
            "location_code": "1005493",
            "device": "mobile",
            "cluster": "segovia",
            "target_url": "https://www.voyagerballoons.eu/en/hot-air-balloon-segovia",
            "priority": "P1",
            "status": "active",
            "impressions": 40,
            "clicks": 2,
            "ctr": 0.05,
            "position": 12,
        }
        candidate, created, activated = self.store.upsert_keyword_candidate(run_id, payload)
        self.assertTrue(created)
        self.assertTrue(activated)
        self.assertEqual(candidate.query, "balloon ride segovia price")

        payload.update({"query": "balloon ride segovia price", "status": "candidate", "impressions": 55})
        _, created_again, activated_again = self.store.upsert_keyword_candidate(run_id, payload)

        self.assertFalse(created_again)
        self.assertFalse(activated_again)
        self.assertEqual(self.store.keyword_candidate_count("active"), 1)
        self.assertEqual(self.store.active_keyword_candidates()[0].impressions, 55)


if __name__ == "__main__":
    unittest.main()
