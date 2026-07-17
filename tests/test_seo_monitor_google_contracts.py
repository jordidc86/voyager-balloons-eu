from __future__ import annotations

import unittest
from datetime import date

from seo_monitor.checks.ga4 import _dimension_report, _report
from seo_monitor.checks.gsc import _query, _totals


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


if __name__ == "__main__":
    unittest.main()
