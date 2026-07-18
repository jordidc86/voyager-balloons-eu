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
from seo_monitor.checks.pagespeed import _failed_category_audits, _field_scope, _performance_opportunities
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

    def test_pagespeed_origin_field_data_is_not_treated_as_page_specific(self) -> None:
        self.assertEqual(
            _field_scope(
                "https://shop.voyagerballoons.eu/producto/comfort/",
                "https://shop.voyagerballoons.eu",
            ),
            ("origin", "https://shop.voyagerballoons.eu"),
        )

    def test_pagespeed_opportunities_are_ranked_by_estimated_savings(self) -> None:
        opportunities = _performance_opportunities({
            "unused-css-rules": {
                "score": 0,
                "displayValue": "Est savings of 43 KiB",
                "details": {"overallSavingsBytes": 44032},
            },
            "render-blocking-insight": {
                "score": 0,
                "displayValue": "Est savings of 1,220 ms",
                "details": {"items": [{"wastedMs": 1220}]},
            },
        })

        self.assertEqual(opportunities[0]["audit"], "render-blocking-insight")
        self.assertEqual(opportunities[0]["savings_ms"], 1220)

    def test_pagespeed_does_not_sum_overlapping_render_delays(self) -> None:
        opportunities = _performance_opportunities({
            "render-blocking-insight": {
                "score": 0,
                "details": {"items": [{"wastedMs": 1220}, {"wastedMs": 980}]},
            },
        })

        self.assertEqual(opportunities[0]["savings_ms"], 1220)

    def test_failed_seo_audits_capture_actionable_nodes(self) -> None:
        failures = _failed_category_audits(
            {"seo": {"auditRefs": [{"id": "crawlable-anchors"}]}},
            {"crawlable-anchors": {
                "score": 0,
                "title": "Links are not crawlable",
                "details": {"items": [{"node": {
                    "selector": "a.ast-qty-placeholder",
                    "snippet": '<a href="javascript:void(0)">',
                }}]},
            }},
            "seo",
        )

        self.assertEqual(failures[0]["id"], "crawlable-anchors")
        self.assertEqual(failures[0]["nodes"][0]["selector"], "a.ast-qty-placeholder")

    @patch("seo_monitor.checks.keyword_demand.requests.post")
    def test_keyword_overview_accepts_null_items(self, post) -> None:
        response = Mock()
        response.json.return_value = {
            "tasks": [{
                "status_code": 20000,
                "cost": 0.012,
                "result": [{"items": None}],
            }],
        }
        post.return_value = response
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")

        items, cost = keyword_demand._overview(settings, ["passeio de balao braganca"], "pt", 2620, "pt")

        self.assertEqual(items, [])
        self.assertEqual(cost, 0.012)

    @patch("seo_monitor.checks.indexing._inspect")
    @patch("seo_monitor.checks.indexing.authorized_session", return_value=Mock())
    def test_unknown_url_is_pending_not_critical(self, authorized_session, inspect) -> None:
        inspect.return_value = {
            "indexStatusResult": {
                "verdict": "NEUTRAL",
                "coverageState": "Google no reconoce esta URL",
                "indexingState": "INDEXING_STATE_UNSPECIFIED",
                "robotsTxtState": "ROBOTS_TXT_STATE_UNSPECIFIED",
                "pageFetchState": "PAGE_FETCH_STATE_UNSPECIFIED",
            },
        }
        settings = replace(Settings.from_env(), google_service_account_json='{"type":"service_account"}')
        config = {
            "strategic_pages": [{
                "name": "Braganca PT",
                "url": "https://www.voyagerballoons.eu/pt/passeio-de-balao-braganca",
                "severity": "P0",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            run_id = store.start_job("indexing")
            result = indexing.run(config, store, run_id, settings)

        self.assertEqual(len(result.alerts), 1)
        self.assertEqual(result.alerts[0].severity, "P2")
        self.assertIn("pendiente", result.alerts[0].title.lower())

    def test_maps_absence_requires_consecutive_observations(self) -> None:
        history = [Mock(position=None), Mock(position=None), Mock(position=4)]
        self.assertEqual(_absence_streak(history, None), 3)
        self.assertEqual(_absence_streak(history, 8), 0)

    def test_maps_two_absences_are_not_enough_for_configured_alert(self) -> None:
        history = [Mock(position=None), Mock(position=4)]
        streak = _absence_streak(history, None)

        self.assertEqual(streak, 2)
        self.assertLess(streak, 3)

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

    @patch("seo_monitor.checks.backlink_gap.requests.post")
    def test_backlink_profile_request_includes_nofollow_domains(self, post) -> None:
        response = Mock()
        response.json.return_value = {
            "tasks": [{"status_code": 20000, "cost": 0.02, "result": [{"items": []}]}],
        }
        post.return_value = response
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")

        backlink_gap._referring_domains(settings, "www.example.com", limit=500, dofollow_only=False)

        payload = post.call_args.kwargs["json"][0]
        self.assertEqual(payload["target"], "example.com")
        self.assertEqual(payload["limit"], 500)
        self.assertNotIn("backlinks_filters", payload)

    @patch("seo_monitor.checks.backlink_gap._referring_domains")
    def test_backlink_profile_requires_two_misses_before_loss_alert(self, referring_domains) -> None:
        original = {
            "domain": "quality.example",
            "rank": 42,
            "backlinks_spam_score": 3,
            "backlinks": 2,
            "referring_pages": 2,
            "referring_pages_nofollow": 0,
            "first_seen": "2026-07-01 10:00:00 +00:00",
        }
        newcomer = {
            "domain": "new.example",
            "rank": 35,
            "backlinks_spam_score": 2,
            "backlinks": 1,
            "referring_pages": 1,
            "referring_pages_nofollow": 0,
            "first_seen": "2026-07-15 10:00:00 +00:00",
        }
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")
        config = {
            "primary_domain": "www.voyagerballoons.eu",
            "backlink_gap_competitors": [],
            "thresholds": {
                "backlink_profile_limit": 500,
                "backlink_profile_minimum_rank": 15,
                "backlink_profile_maximum_spam_score": 30,
                "backlink_profile_loss_confirmations": 2,
                "dataforseo_run_budget_usd": 1,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()

            referring_domains.return_value = ([original], 0.02)
            first_run = store.start_job("backlink_gap")
            first = backlink_gap.run(config, store, first_run, settings)
            store.save_result(first_run, first)
            self.assertFalse(first.summary["profile_baseline_initialized"])
            self.assertFalse(any("Nuevos dominios" in alert.title for alert in first.alerts))

            referring_domains.return_value = ([newcomer], 0.02)
            second_run = store.start_job("backlink_gap")
            second = backlink_gap.run(config, store, second_run, settings)
            store.save_result(second_run, second)
            self.assertEqual(second.summary["profile_new_domains"], 1)
            self.assertEqual(second.summary["profile_missing_once"], 1)
            self.assertEqual(second.summary["profile_confirmed_lost"], 0)
            self.assertFalse(any("perdido" in alert.title.lower() for alert in second.alerts))

            third_run = store.start_job("backlink_gap")
            third = backlink_gap.run(config, store, third_run, settings)
            store.save_result(third_run, third)
            self.assertEqual(third.summary["profile_confirmed_lost"], 1)
            self.assertTrue(any("quality.example" in alert.title for alert in third.alerts))

            referring_domains.return_value = ([original, newcomer], 0.02)
            fourth_run = store.start_job("backlink_gap")
            fourth = backlink_gap.run(config, store, fourth_run, settings)
            store.save_result(fourth_run, fourth)
            self.assertEqual(fourth.summary["profile_recovered_domains"], 1)
            self.assertFalse(any("quality.example" in alert.title for alert in fourth.alerts))
            self.assertFalse(any(alert.dedupe_key == "backlink_gap:lost:quality.example" for alert in store.open_alerts()))

    @patch("seo_monitor.checks.backlink_gap._referring_domains", side_effect=RuntimeError("provider unavailable"))
    def test_backlink_profile_provider_failure_does_not_claim_success(self, referring_domains) -> None:
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")
        config = {
            "primary_domain": "www.voyagerballoons.eu",
            "backlink_gap_competitors": [],
            "thresholds": {"dataforseo_run_budget_usd": 1},
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            run_id = store.start_job("backlink_gap")

            result = backlink_gap.run(config, store, run_id, settings)

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.summary["failures"], 1)
        self.assertTrue(any(alert.dedupe_key == "backlink_gap:provider-failures" for alert in result.alerts))

    @patch("seo_monitor.checks.backlink_gap._referring_domains")
    def test_backlink_gap_keeps_weak_candidates_without_recommending_them(self, referring_domains) -> None:
        weak = {
            "domain": "directory.example",
            "rank": 15,
            "backlinks_spam_score": 0,
            "backlinks": 3,
            "referring_pages": 3,
            "referring_pages_nofollow": 0,
            "referring_links_platform_types": {"organization": 3},
        }
        settings = replace(Settings.from_env(), dataforseo_login="login", dataforseo_password="password")
        config = {
            "primary_domain": "www.voyagerballoons.eu",
            "backlink_gap_competitors": [{"name": "Competitor", "domain": "competitor.example"}],
            "thresholds": {
                "backlink_gap_minimum_rank": 12,
                "backlink_gap_maximum_spam_score": 30,
                "backlink_gap_minimum_score": 35,
                "dataforseo_run_budget_usd": 1,
            },
        }
        referring_domains.side_effect = [([], 0.02), ([weak], 0.02)]
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(f"sqlite:///{Path(tmp) / 'monitor.db'}")
            store.initialize()
            run_id = store.start_job("backlink_gap")

            result = backlink_gap.run(config, store, run_id, settings)

        self.assertEqual(result.summary["candidates_discovered"], 1)
        self.assertEqual(result.summary["qualified_opportunities"], 0)
        self.assertFalse(any(alert.dedupe_key == "backlink_gap:qualified-opportunities" for alert in result.alerts))

    @patch("seo_monitor.checks.keyword_demand._overview")
    @patch("seo_monitor.checks.keyword_demand.load_keyword_inventory")
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

        self.assertEqual(overview.call_args.args[2:4], ("en", 2724))
        self.assertEqual(result.summary["keywords_with_data"], 1)
        self.assertEqual(result.summary["opportunities"], 1)
        self.assertEqual(result.summary["provider_cost_usd"], 0.012)

    def test_keyword_demand_uses_each_language_in_the_portugal_market(self) -> None:
        self.assertEqual(
            keyword_demand._market({"cluster": "braganca_en", "language_code": "en"}),
            ("Portugal", "en", 2620),
        )
        self.assertEqual(
            keyword_demand._market({"cluster": "braganca", "language_code": "es"}),
            ("Portugal", "es", 2620),
        )

    @patch("seo_monitor.checks.rank._search")
    @patch("seo_monitor.checks.rank.load_keyword_inventory")
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

        with patch("seo_monitor.checks.rank.load_keyword_inventory", return_value=[{
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
