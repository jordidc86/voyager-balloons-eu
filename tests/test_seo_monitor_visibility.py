from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from seo_monitor.checks.ai_visibility import _extract_response
from seo_monitor.checks.local_visibility import _absence_streak, _drop_assessment as _maps_drop, _rating
from seo_monitor.config import Settings, load_config
from seo_monitor.storage import Store
from seo_monitor.checks import ai_visibility, backlink_gap, indexing, keyword_demand, local_visibility, rank
from seo_monitor.google_auth import authorized_session


class VisibilityTests(unittest.TestCase):
    @patch("seo_monitor.google_auth.AuthorizedSession")
    @patch("seo_monitor.google_auth.service_account.Credentials.from_service_account_info")
    def test_google_credentials_json_is_not_treated_as_a_path(self, from_info, session_class) -> None:
        from_info.return_value = object()
        authorized_session('{"type":"service_account"}', ["scope"])
        from_info.assert_called_once_with({"type": "service_account"}, scopes=["scope"])
        session_class.assert_called_once_with(from_info.return_value)

    def test_ai_response_text_and_citations_are_extracted(self) -> None:
        text, citations = _extract_response({
            "items": [{
                "type": "message",
                "sections": [{
                    "type": "text",
                    "text": "Voyager Balloons is an option.",
                    "annotations": [{"title": "Voyager", "url": "https://www.voyagerballoons.eu/"}],
                }],
            }],
        })
        self.assertIn("Voyager Balloons", text)
        self.assertEqual(citations[0]["url"], "https://www.voyagerballoons.eu/")

    @patch("seo_monitor.checks.ai_visibility.requests.post")
    def test_ai_provider_payloads_only_use_supported_localization(self, post) -> None:
        response = Mock()
        response.json.return_value = {
            "tasks": [{
                "status_code": 20000,
                "cost": 0.01,
                "result": [{"items": []}],
            }],
        }
        post.return_value = response
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")
        prompt = {
            "id": "pt-braganca",
            "prompt": "Passeio de balao em Braganca?",
            "country": "PT",
            "city": "Braganca",
        }

        for name, model_name in (
            ("chat_gpt", "gpt-4.1-mini"),
            ("gemini", "gemini-2.5-flash"),
            ("perplexity", "sonar"),
        ):
            ai_visibility._ask(settings, {"name": name, "model_name": model_name}, prompt)

        chat_gpt = post.call_args_list[0].kwargs["json"][0]
        gemini = post.call_args_list[1].kwargs["json"][0]
        perplexity = post.call_args_list[2].kwargs["json"][0]
        self.assertEqual(chat_gpt["web_search_city"], "Braganca")
        self.assertEqual(chat_gpt["web_search_country_iso_code"], "PT")
        self.assertTrue(gemini["web_search"])
        self.assertNotIn("web_search_city", gemini)
        self.assertNotIn("web_search_country_iso_code", gemini)
        self.assertEqual(perplexity["web_search_country_iso_code"], "PT")
        self.assertNotIn("web_search_city", perplexity)
        self.assertNotIn("web_search", perplexity)

    def test_maps_rating_object_is_normalized(self) -> None:
        self.assertEqual(_rating({"rating": {"value": 4.9, "votes_count": 365}}), (4.9, 365))

    def test_maps_absence_requires_consecutive_observations(self) -> None:
        history = [Mock(position=None), Mock(position=None), Mock(position=4)]
        self.assertEqual(_absence_streak(history, None), 3)
        self.assertEqual(_absence_streak(history, 8), 0)

    def test_maps_drop_requires_stable_history_and_confirmation(self) -> None:
        history = [Mock(position=8), Mock(position=3), Mock(position=3)]
        drop = _maps_drop(history, 8, 3)
        self.assertIsNotNone(drop)
        self.assertTrue(drop["confirmed"])
        self.assertEqual(drop["baseline"], 3)

    def test_paid_visibility_jobs_skip_cleanly_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            settings = replace(Settings.from_env(), dataforseo_login=None, dataforseo_password=None)
            config = load_config(settings)

            local_run = store.start_job("local_visibility")
            local_result = local_visibility.run(config, store, local_run, settings)
            self.assertEqual(local_result.status, "skipped")

            ai_run = store.start_job("ai_visibility")
            ai_result = ai_visibility.run(config, store, ai_run, settings)
            self.assertEqual(ai_result.status, "skipped")

            gap_run = store.start_job("backlink_gap")
            gap_result = backlink_gap.run(config, store, gap_run, settings)
            self.assertEqual(gap_result.status, "skipped")

            demand_run = store.start_job("keyword_demand")
            demand_result = keyword_demand.run(config, store, demand_run, settings)
            self.assertEqual(demand_result.status, "skipped")

            indexing_run = store.start_job("indexing")
            indexing_result = indexing.run(config, store, indexing_run, settings)
            self.assertEqual(indexing_result.status, "skipped")

    @patch("seo_monitor.checks.backlink_gap.requests.post")
    def test_backlink_gap_uses_referring_domains_for_each_target(self, post) -> None:
        response = Mock()
        response.json.return_value = {
            "tasks": [{"status_code": 20000, "cost": 0.02, "result": [{"items": []}]}],
        }
        post.return_value = response
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")

        backlink_gap._referring_domains(settings, "www.example.com")

        payload = post.call_args.kwargs["json"][0]
        self.assertEqual(payload["target"], "example.com")
        self.assertEqual(payload["order_by"], ["rank,desc"])
        self.assertEqual(payload["backlinks_filters"], ["dofollow", "=", True])

    @patch("seo_monitor.checks.keyword_demand._overview")
    @patch("seo_monitor.checks.keyword_demand.load_keywords")
    def test_keyword_demand_uses_native_market_language_and_records_opportunity(self, load_keywords, overview) -> None:
        load_keywords.return_value = [{
            "keyword": "hot air balloon segovia",
            "location_name": "Madrid Spain",
            "language_code": "en",
            "device": "mobile",
            "priority": "P0",
            "target_url": "https://www.voyagerballoons.eu/en/hot-air-balloon-segovia",
            "cluster": "segovia_en",
        }]
        overview.return_value = ([{
            "keyword": "hot air balloon segovia",
            "keyword_info": {"search_volume": 50, "cpc": 5.01, "competition": 1, "competition_level": "HIGH"},
            "search_intent_info": {"main_intent": "commercial"},
            "keyword_properties": {"keyword_difficulty": 0},
        }], 0.012)
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")
        config = load_config(settings)
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            run_id = store.start_job("keyword_demand")
            result = keyword_demand.run(config, store, run_id, settings)

        self.assertEqual(overview.call_args.args[2:4], ("es", 2724))
        self.assertEqual(result.summary["keywords_with_data"], 1)
        self.assertEqual(result.summary["opportunities"], 1)
        self.assertEqual(result.summary["provider_cost_usd"], 0.012)

    @patch("seo_monitor.checks.rank._search")
    @patch("seo_monitor.checks.rank.load_keywords")
    def test_rank_run_uses_configured_thresholds(self, load_keywords, search) -> None:
        load_keywords.return_value = [{
            "keyword": "paseo en globo braganza",
            "location_name": "Braganza,Portugal",
            "language_code": "es",
            "device": "desktop",
            "priority": "P0",
            "target_url": "https://www.voyagerballoons.eu/es/braganza",
            "cluster": "braganza",
        }]
        search.return_value = ({
            "items": [{
                "type": "organic",
                "rank_absolute": 3,
                "url": "https://www.voyagerballoons.eu/es/braganza",
            }],
            "check_url": "https://example.test/serp",
        }, 0.002)

        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            settings = replace(
                Settings.from_env(),
                dataforseo_login="login",
                dataforseo_password="password",
            )
            config = load_config(settings)
            run_id = store.start_job("rank")

            result = rank.run(config, store, run_id, settings)

        search.assert_called_once()
        self.assertEqual(search.call_args.args[2], config["thresholds"]["rank_critical_depth"])
        self.assertEqual(result.summary["keywords_checked"], 1)
        self.assertEqual(result.summary["found_top_10"], 1)

    @patch("seo_monitor.checks.rank.requests.post")
    def test_rank_search_prefers_stable_location_code(self, post) -> None:
        response = Mock()
        response.json.return_value = {
            "tasks": [{
                "status_code": 20000,
                "cost": 0.002,
                "result": [{"items": [], "check_url": "https://example.test/serp"}],
            }],
        }
        post.return_value = response
        settings = replace(
            Settings.from_env(),
            dataforseo_login="login",
            dataforseo_password="password",
        )

        rank._search(settings, {
            "keyword": "paseo en globo braganza",
            "location_name": "Braganca Portugal",
            "location_code": "9051350",
            "language_code": "es",
            "device": "mobile",
        }, 20)

        payload = post.call_args.kwargs["json"][0]
        self.assertEqual(payload["location_code"], 9051350)
        self.assertNotIn("location_name", payload)

    @patch("seo_monitor.checks.rank.time.sleep")
    @patch("seo_monitor.checks.rank.requests.post")
    def test_rank_search_retries_transient_provider_errors(self, post, sleep) -> None:
        failed = Mock()
        failed.json.return_value = {
            "tasks": [{"status_code": 50000, "status_message": "Internal SE Server Error.", "cost": 0}],
        }
        succeeded = Mock()
        succeeded.json.return_value = {
            "tasks": [{
                "status_code": 20000,
                "cost": 0.002,
                "result": [{"items": [], "check_url": "https://example.test/serp"}],
            }],
        }
        post.side_effect = [failed, succeeded]
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")

        _, cost = rank._search(settings, {
            "keyword": "vuelo en globo comfort segovia",
            "location_name": "Madrid Spain",
            "location_code": "1005493",
            "language_code": "es",
            "device": "mobile",
        }, 20)

        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1)
        self.assertEqual(cost, 0.002)

    @patch("seo_monitor.checks.rank.time.sleep")
    @patch("seo_monitor.checks.rank.requests.post")
    def test_rank_run_counts_cost_of_failed_provider_attempts(self, post, sleep) -> None:
        failed = Mock()
        failed.json.return_value = {
            "tasks": [{"status_code": 50000, "status_message": "Internal SE Server Error.", "cost": 0.01}],
        }
        post.return_value = failed
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")
        config = load_config(settings)

        with patch("seo_monitor.checks.rank.load_keywords", return_value=[{
            "keyword": "hot air balloon madrid day trip",
            "location_name": "Madrid Spain",
            "location_code": "1005493",
            "language_code": "en",
            "device": "mobile",
            "priority": "P0",
            "target_url": "https://www.voyagerballoons.eu/en/hot-air-balloon-segovia-from-madrid",
            "cluster": "madrid_en",
        }]), tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            run_id = store.start_job("rank")
            result = rank.run(config, store, run_id, settings)

        self.assertEqual(result.summary["failures"], 1)
        self.assertEqual(result.summary["provider_cost_usd"], 0.03)
        self.assertEqual(post.call_count, 3)


if __name__ == "__main__":
    unittest.main()
