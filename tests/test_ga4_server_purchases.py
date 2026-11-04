import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from seo_monitor.checks import ga4
from seo_monitor.storage import Store


SHOP = "tienda.voyagerballoons.eu"
LEGACY = "shop.voyagerballoons.eu"
ROWS = [
    {"eventName": "add_to_cart", "hostName": SHOP, "eventCount": 266},
    {"eventName": "begin_checkout", "hostName": SHOP, "eventCount": 43},
    {"eventName": "purchase", "hostName": "(not set)", "eventCount": 27, "totalRevenue": 6834},
]
SESSIONS = [{"hostName": SHOP, "sessions": 100, "sessionDefaultChannelGroup": "Direct"}]


class ServerPurchaseTests(unittest.TestCase):
    def diagnose(self, rows=ROWS, **kwargs):
        return ga4._commerce_diagnostics(rows, SESSIONS, SHOP, **kwargs)

    def test_server_purchases_prevent_false_zero_and_preserve_provenance(self):
        d = self.diagnose(include_unassigned_purchases=True)
        self.assertEqual((d["purchases"], d["purchase_revenue"]), (27, 6834))
        self.assertEqual((d["unassigned_purchases"], d["unassigned_purchase_revenue"]), (27, 6834))
        self.assertEqual((d["begin_checkout"], d["add_to_cart"]), (43, 266))
        self.assertFalse(d["purchase_missing"])

    def test_unassigned_requires_explicit_opt_in(self):
        self.assertTrue(self.diagnose()["purchase_missing"])

    def test_real_zero_still_alerts(self):
        self.assertTrue(self.diagnose(ROWS[:2], include_unassigned_purchases=True)["purchase_missing"])

    def test_legacy_and_technical_purchases_cannot_hide_missing_purchase(self):
        for host in (LEGACY, "localhost", "127.0.0.1", "other.example"):
            with self.subTest(host=host):
                rows = ROWS[:2] + [{"eventName": "purchase", "hostName": host, "eventCount": 10}]
                self.assertTrue(self.diagnose(rows, include_unassigned_purchases=True)["purchase_missing"])

    def test_unknown_funnel_and_sessions_are_not_assigned_to_shop(self):
        rows = [{"eventName": name, "hostName": "(not set)", "eventCount": 20}
                for name in ("add_to_cart", "begin_checkout")]
        d = self.diagnose(rows, include_unassigned_purchases=True)
        self.assertEqual((d["add_to_cart"], d["begin_checkout"]), (0, 0))
        self.assertTrue(d["funnel_missing"])
        self.assertEqual(d["shop_sessions"], 100)

    def test_browser_and_server_rows_are_summed_once(self):
        rows = ROWS + [{"eventName": "purchase", "hostName": SHOP, "eventCount": 2, "totalRevenue": 258}]
        d = self.diagnose(rows, include_unassigned_purchases=True)
        self.assertEqual((d["purchases"], d["purchase_revenue"]), (29, 7092))
        self.assertEqual(d["unassigned_purchases"], 27)

    def test_empty_hostname_variants(self):
        for host in (None, "", "(not set)"):
            with self.subTest(host=host):
                rows = ROWS[:2] + [{**ROWS[2], "hostName": host}]
                self.assertEqual(self.diagnose(rows, include_unassigned_purchases=True)["purchases"], 27)

    @patch.object(ga4, "authorized_session")
    @patch.object(ga4, "_report", return_value={})
    @patch.object(ga4, "_dimension_report", return_value=[])
    @patch.object(ga4, "_multi_dimension_report")
    def test_full_check_resolves_stale_alert_without_mixing_legacy(self, report, *_):
        report.side_effect = lambda *a, **kw: ROWS if a[4] == ["eventName", "hostName"] else SESSIONS if a[4] == ["sessionDefaultChannelGroup", "hostName"] else []
        config = json.loads((Path(__file__).parents[1] / "config/seo-monitor.json").read_text())
        settings = SimpleNamespace(google_service_account_json="test", ga4_property_id="test")
        store = Store("sqlite:///:memory:")
        store.initialize()
        # Establish the old false alert using the old strict-host behavior.
        old_config = {**config, "tracking": {**config["tracking"], "ga4_unassigned_purchase_store_domain": ""}}
        old = ga4.run(old_config, None, 0, settings)
        store.save_result(store.start_job("ga4"), old)
        self.assertIn("ga4:purchase-events-missing", [a.dedupe_key for a in store.open_alerts()])
        result = ga4.run(config, None, 0, settings)
        self.assertEqual(result.summary["commerce_diagnostics"]["purchases"], 27)
        self.assertEqual(result.summary["current_store_diagnostics"]["purchases"], 27)
        self.assertEqual(result.summary["legacy_shop_diagnostics"]["purchases"], 0)
        changed = store.save_result(store.start_job("ga4"), result)
        self.assertEqual([(a.dedupe_key, a.status) for a in changed], [("ga4:purchase-events-missing", "resolved")])
        self.assertEqual(store.open_alerts(), [])


if __name__ == "__main__":
    unittest.main()
