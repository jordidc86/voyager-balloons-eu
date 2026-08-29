from __future__ import annotations

import unittest

from seo_monitor.checks.tracking import _audit


class TrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "main_script_url": "https://www.voyagerballoons.eu/js/google-ads-tracking.js",
            "main_domain": "voyagerballoons.eu",
            "store_domain": "tienda.voyagerballoons.eu",
            "google_tag_id": "GT-55NTF5CN",
            "google_ads_id": "AW-11564692382",
        }
        self.main = (
            '<script src="/js/google-ads-tracking.js"></script>'
            '<a href="https://tienda.voyagerballoons.eu/">Reservar</a>'
        )
        self.linker = "voyagerballoons.eu tienda.voyagerballoons.eu accept_incoming decorate_forms"
        self.script = (
            f"GT-55NTF5CN AW-11564692382 {self.linker} "
            "vb_landing_path vb_referrer_host utm_source"
        )
        self.store = (
            f"GT-55NTF5CN AW-11564692382 {self.linker} voyager-google-tag-bootstrap "
            "voyager-tracking-contract add_to_cart begin_checkout"
        )

    def test_complete_tracking_contract_passes(self) -> None:
        findings = _audit(self.main, self.script, self.store, self.config)
        self.assertEqual(len(findings), 8)
        self.assertTrue(all(item["ok"] for item in findings))

    def test_missing_journey_attribution_fails(self) -> None:
        findings = _audit(self.main, self.linker, self.store, self.config)
        check = next(item for item in findings if item["key"] == "journey-attribution")
        self.assertFalse(check["ok"])

    def test_missing_store_funnel_contract_fails_without_requiring_purchase(self) -> None:
        store = self.store.replace("add_to_cart", "").replace("begin_checkout", "")
        findings = _audit(self.main, self.script, store, self.config)
        check = next(item for item in findings if item["key"] == "store-funnel-contract")
        self.assertFalse(check["ok"])
        self.assertNotIn("purchase", check["message"])

    def test_legacy_shop_does_not_satisfy_active_store_link(self) -> None:
        main = self.main.replace("tienda.voyagerballoons.eu", "shop.voyagerballoons.eu")
        findings = _audit(main, self.script, self.store, self.config)
        check = next(item for item in findings if item["key"] == "store-links")
        self.assertFalse(check["ok"])


if __name__ == "__main__":
    unittest.main()
