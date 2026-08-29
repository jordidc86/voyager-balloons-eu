from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from seo_monitor.checks import commerce
from seo_monitor.types import AlertSpec


class FakeResponse:
    def __init__(self, *, text="", payload=None, url="https://example.test", status_code=200):
        self.text = text
        self.payload = payload
        self.url = url
        self.status_code = status_code

    def json(self):
        if self.payload is None:
            raise ValueError("not json")
        return self.payload


class CommerceTests(unittest.TestCase):
    @patch("seo_monitor.checks.commerce.requests.get")
    def test_page_probe_validates_content_and_noindex(self, get: Mock) -> None:
        get.return_value = FakeResponse(
            text='<meta name="robots" content="noindex, follow"><main>Prepara tu vuelo Classic 120</main>',
        )
        probe = {
            "name": "Reserva Classic",
            "url": "https://example.test/reservar",
            "expected_text": ["Prepara tu vuelo", "Classic", "120"],
            "expected_robots": "noindex",
        }

        outcome, alerts = commerce.test_probe(probe, 5)

        self.assertTrue(outcome["flow_ok"])
        self.assertEqual(alerts, [])

    @patch("seo_monitor.checks.commerce.requests.get")
    def test_json_probe_validates_production_contract(self, get: Mock) -> None:
        get.return_value = FakeResponse(payload={
            "ok": True,
            "app": "voyager-booking-store",
            "mode": "production",
        })
        probe = {
            "name": "Salud tienda",
            "kind": "json",
            "url": "https://example.test/api/health",
            "expected_json": {
                "ok": True,
                "app": "voyager-booking-store",
                "mode": "production",
            },
        }

        outcome, alerts = commerce.test_probe(probe, 5)

        self.assertTrue(outcome["flow_ok"])
        self.assertEqual(alerts, [])

    @patch("seo_monitor.checks.commerce.test_probe")
    def test_summary_never_counts_an_alerted_flow_as_successful(self, test_probe: Mock) -> None:
        probe = {"name": "Reserva", "url": "https://example.test"}
        alert = AlertSpec(
            dedupe_key="commerce:content:reserva",
            severity="P0",
            category="commerce",
            title="Broken",
            message="Broken",
            action="Fix",
        )
        test_probe.return_value = ({"probe": "Reserva", "flow_ok": False}, [alert])

        result = commerce.run(
            {"thresholds": {}, "commerce_probes": [probe]},
            store=None,
            run_id=1,
        )

        self.assertEqual(result.summary["successful_flows"], 0)
        self.assertEqual(result.summary["alerts"], 1)
        self.assertEqual(result.resolution_prefixes, ["commerce:"])

if __name__ == "__main__":
    unittest.main()
