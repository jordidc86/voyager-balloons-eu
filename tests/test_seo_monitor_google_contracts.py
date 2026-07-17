from __future__ import annotations

import unittest
from datetime import date

from seo_monitor.checks.ga4 import _commerce_diagnostics, _dimension_report, _funnel_window, _report
from seo_monitor.checks.gsc import _discover_keyword_candidates, _query, _totals


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def post(self, endpoint: str, json: dict, timeout: int):
        self.calls.append({"endpoint": endpoint, "json": json, "timeout": timeout})
        return FakeResponse(self.payload)


class GoogleContractTests(unittest.TestCase):
    def test_search_console_query_uses_final_web_data(self) -> None:
        session = FakeSession({"rows": [{"keys": ["query"], "clicks": 3, "impressions": 100}]})
        rows = _query(session, "sc-domain:voyagerballoons.eu", date(2026, 7, 1), date(2026, 7, 7), ["query"])
        self.assertEqual(rows[0]["clicks"], 3)
        body = session.calls[0]["json"]
        self.assertEqual(body["dimensions"], ["query"])
        self.assertEqual(body["dataState"], "final")
        self.assertEqual(body["type"], "web")

    def test_search_console_totals_handle_empty_data(self) -> None:
        self.assertEqual(_totals([]), {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0})

    def test_gsc_discovers_commercial_query_and_chooses_best_landing(self) -> None:
        rows = [
            {
                "keys": ["balloon ride segovia price", "https://www.voyagerballoons.eu/en/"],
                "clicks": 0,
                "impressions": 15,
                "position": 18,
            },
            {
                "keys": ["balloon ride segovia price", "https://www.voyagerballoons.eu/en/hot-air-balloon-segovia"],
                "clicks": 2,
                "impressions": 25,
                "position": 9,
            },
            {
                "keys": ["voyager balloons", "https://www.voyagerballoons.eu/"],
                "clicks": 5,
                "impressions": 100,
                "position": 1,
            },
            {
                "keys": ["globos boreal segovia", "https://www.voyagerballoons.eu/"],
                "clicks": 0,
                "impressions": 120,
                "position": 16,
            },
        ]

        candidates = _discover_keyword_candidates(
            rows,
            existing_keywords=set(),
            discovery_config={
                "minimum_impressions_28d": 20,
                "excluded_terms": ["voyager", "globos boreal"],
            },
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["query"], "balloon ride segovia price")
        self.assertEqual(candidates[0]["language_code"], "en")
        self.assertEqual(candidates[0]["impressions"], 40)
        self.assertEqual(candidates[0]["target_url"], "https://www.voyagerballoons.eu/en/hot-air-balloon-segovia")

    def test_gsc_discovery_rejects_technical_and_parameterized_pages(self) -> None:
        rows = [
            {
                "keys": ["balloon ride segovia", "https://shop.voyagerballoons.eu/cart/"],
                "clicks": 3,
                "impressions": 100,
                "position": 4,
            },
            {
                "keys": ["balloon ride segovia", "https://www.voyagerballoons.eu/en/?preview=true"],
                "clicks": 2,
                "impressions": 80,
                "position": 5,
            },
        ]

        self.assertEqual(_discover_keyword_candidates(rows, set(), {}), [])

    def test_ga4_dimension_report_maps_headers_and_values(self) -> None:
        session = FakeSession({
            "metricHeaders": [{"name": "sessions"}, {"name": "keyEvents"}],
            "rows": [{
                "dimensionValues": [{"value": "/vuelo-en-globo-segovia"}],
                "metricValues": [{"value": "12"}, {"value": "2"}],
            }],
        })
        rows = _dimension_report(
            session,
            "123456",
            date(2026, 7, 1),
            date(2026, 7, 7),
            "landingPagePlusQueryString",
            ["sessions", "keyEvents"],
        )
        self.assertEqual(rows[0]["landingPagePlusQueryString"], "/vuelo-en-globo-segovia")
        self.assertEqual(rows[0]["sessions"], 12)
        self.assertEqual(rows[0]["keyEvents"], 2)
        self.assertEqual(
            session.calls[0]["json"]["dimensionFilter"]["filter"]["stringFilter"]["value"],
            "Organic Search",
        )

    def test_ga4_totals_handle_empty_rows(self) -> None:
        session = FakeSession({"metricHeaders": [{"name": "sessions"}], "rows": []})
        self.assertEqual(_report(session, "123456", date(2026, 7, 1), date(2026, 7, 7)), {})

    def test_ga4_commerce_diagnostics_detect_missing_funnel_events(self) -> None:
        diagnostics = _commerce_diagnostics(
            [{
                "eventName": "purchase", "hostName": "shop.voyagerballoons.eu",
                "eventCount": 2, "keyEvents": 2, "totalRevenue": 480,
            }],
            [
                {"sessionDefaultChannelGroup": "Organic Search", "hostName": "shop.voyagerballoons.eu", "sessions": 120},
                {"sessionDefaultChannelGroup": "Direct", "hostName": "shop.voyagerballoons.eu", "sessions": 30},
                {"sessionDefaultChannelGroup": "Direct", "hostName": "localhost", "sessions": 12},
            ],
            "shop.voyagerballoons.eu",
        )

        self.assertTrue(diagnostics["funnel_missing"])
        self.assertTrue(diagnostics["add_to_cart_missing"])
        self.assertTrue(diagnostics["begin_checkout_missing"])
        self.assertEqual(diagnostics["purchases"], 2)
        self.assertEqual(diagnostics["purchase_revenue"], 480)
        self.assertEqual(diagnostics["shop_direct_share_percent"], 20.0)
        self.assertEqual(diagnostics["technical_sessions"], 12)

    def test_ga4_funnel_does_not_alert_during_post_fix_warmup(self) -> None:
        diagnostics = _commerce_diagnostics(
            [],
            [{
                "sessionDefaultChannelGroup": "Organic Search",
                "hostName": "shop.voyagerballoons.eu",
                "sessions": 150,
            }],
            "shop.voyagerballoons.eu",
            minimum_shop_sessions=50,
            evaluation_ready=False,
        )

        self.assertFalse(diagnostics["evaluation_ready"])
        self.assertFalse(diagnostics["funnel_missing"])
        self.assertFalse(diagnostics["add_to_cart_missing"])
        self.assertFalse(diagnostics["begin_checkout_missing"])

    def test_ga4_funnel_window_starts_after_tracking_fix(self) -> None:
        config = {
            "tracking": {"funnel_tracking_start_date": "2026-07-17"},
            "thresholds": {"ga4_funnel_minimum_complete_days": 2},
        }

        start, complete_days, ready = _funnel_window(
            config,
            date(2026, 7, 17),
            date(2026, 6, 20),
        )

        self.assertEqual(start, date(2026, 7, 17))
        self.assertEqual(complete_days, 1)
        self.assertFalse(ready)


if __name__ == "__main__":
    unittest.main()
