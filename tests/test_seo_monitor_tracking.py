from __future__ import annotations

import unittest

from seo_monitor.checks.tracking import _audit


class TrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "main_script_url": "https://www.voyagerballoons.eu/js/google-ads-tracking.js",
            "main_domain": "voyagerballoons.eu",
            "shop_domain": "shop.voyagerballoons.eu",
            "google_tag_id": "GT-55NTF5CN",
            "google_ads_id": "AW-11564692382",
        }

    def test_complete_tracking_contract_passes(self) -> None:
        main = '<script src="/js/google-ads-tracking.js"></script><a href="https://shop.voyagerballoons.eu/">Shop</a>'
        linker = "voyagerballoons.eu shop.voyagerballoons.eu accept_incoming decorate_forms"
        script = f'GT-55NTF5CN AW-11564692382 {linker}'
        shop = f'GT-55NTF5CN AW-11564692382 {linker} eventsToTrack add_to_cart purchase'
        findings = _audit(main, script, shop, self.config)
        self.assertTrue(all(item["ok"] for item in findings))

    def test_missing_purchase_event_fails(self) -> None:
        main = f'{self.config["main_script_url"]} shop.voyagerballoons.eu'
        linker = "voyagerballoons.eu shop.voyagerballoons.eu accept_incoming decorate_forms"
        script = f'GT-55NTF5CN AW-11564692382 {linker}'
        shop = f'GT-55NTF5CN AW-11564692382 {linker} eventsToTrack add_to_cart'
        findings = _audit(main, script, shop, self.config)
        purchase_check = next(item for item in findings if item["key"] == "woocommerce-events")
        self.assertFalse(purchase_check["ok"])


if __name__ == "__main__":
    unittest.main()
