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
        shop = (
            f'GT-55NTF5CN AW-11564692382 {linker} eventsToTrack add_to_cart purchase '
            'voyager_begin_checkout siteKit.gtagEvent("begin_checkout", {}) '
            '<script id="googlesitekit-events-provider-woocommerce-js" src="provider.js"></script>'
        )
        findings = _audit(main, script, shop, self.config)
        self.assertTrue(all(item["ok"] for item in findings))

    def test_missing_purchase_event_fails(self) -> None:
        main = f'{self.config["main_script_url"]} shop.voyagerballoons.eu'
        linker = "voyagerballoons.eu shop.voyagerballoons.eu accept_incoming decorate_forms"
        script = f'GT-55NTF5CN AW-11564692382 {linker}'
        shop = (
            f'GT-55NTF5CN AW-11564692382 {linker} eventsToTrack add_to_cart '
            'voyager_begin_checkout siteKit.gtagEvent("begin_checkout", {}) '
            '<script id="googlesitekit-events-provider-woocommerce-js" src="provider.js"></script>'
        )
        findings = _audit(main, script, shop, self.config)
        purchase_check = next(item for item in findings if item["key"] == "woocommerce-events")
        self.assertFalse(purchase_check["ok"])

    def test_delayed_woocommerce_listener_fails(self) -> None:
        main = f'{self.config["main_script_url"]} shop.voyagerballoons.eu'
        linker = "voyagerballoons.eu shop.voyagerballoons.eu accept_incoming decorate_forms"
        script = f'GT-55NTF5CN AW-11564692382 {linker}'
        shop = (
            f'GT-55NTF5CN AW-11564692382 {linker} eventsToTrack add_to_cart purchase '
            'voyager_begin_checkout siteKit.gtagEvent("begin_checkout", {}) '
            '<script type="rocketlazyloadscript" id="googlesitekit-events-provider-woocommerce-js" '
            'data-rocket-src="provider.js"></script>'
        )
        findings = _audit(main, script, shop, self.config)
        listener_check = next(item for item in findings if item["key"] == "woocommerce-listener-immediate")
        self.assertFalse(listener_check["ok"])

    def test_missing_begin_checkout_snippet_fails(self) -> None:
        main = f'{self.config["main_script_url"]} shop.voyagerballoons.eu'
        linker = "voyagerballoons.eu shop.voyagerballoons.eu accept_incoming decorate_forms"
        script = f'GT-55NTF5CN AW-11564692382 {linker}'
        shop = (
            f'GT-55NTF5CN AW-11564692382 {linker} eventsToTrack add_to_cart purchase '
            '<script id="googlesitekit-events-provider-woocommerce-js" src="provider.js"></script>'
        )
        findings = _audit(main, script, shop, self.config)
        checkout_check = next(item for item in findings if item["key"] == "woocommerce-begin-checkout")
        self.assertFalse(checkout_check["ok"])


if __name__ == "__main__":
    unittest.main()
