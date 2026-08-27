from __future__ import annotations

import unittest

from seo_monitor.checks.tracking import _audit


class TrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "main_script_url": "https://www.voyagerballoons.eu/js/google-ads-tracking.js",
            "main_url": "https://www.voyagerballoons.eu/",
            "booking_domain": "tienda.voyagerballoons.eu",
            "main_domain": "voyagerballoons.eu",
            "google_tag_id": "GT-55NTF5CN",
            "google_ads_id": "AW-11564692382",
        }

    def test_complete_tracking_contract_passes(self) -> None:
        main = '<script src="/js/google-ads-tracking.js"></script><a href="https://tienda.voyagerballoons.eu/">Tienda</a>'
        script = (
            "GT-55NTF5CN AW-11564692382 voyagerballoons.eu "
            "tienda.voyagerballoons.eu accept_incoming decorate_forms"
        )

        findings = _audit(main, script, self.config)

        self.assertTrue(all(item["ok"] for item in findings))

    def test_missing_main_script_fails(self) -> None:
        script = (
            "GT-55NTF5CN AW-11564692382 voyagerballoons.eu "
            "tienda.voyagerballoons.eu accept_incoming decorate_forms"
        )
        findings = _audit('<a href="https://tienda.voyagerballoons.eu/">Tienda</a>', script, self.config)

        check = next(item for item in findings if item["key"] == "main-script")

        self.assertFalse(check["ok"])

    def test_missing_cross_domain_configuration_fails(self) -> None:
        main = '<script src="/js/google-ads-tracking.js"></script><a href="https://tienda.voyagerballoons.eu/">Tienda</a>'
        script = "GT-55NTF5CN AW-11564692382 voyagerballoons.eu"

        findings = _audit(main, script, self.config)
        check = next(item for item in findings if item["key"] == "main-linker")

        self.assertFalse(check["ok"])

    def test_booking_link_check_uses_current_store(self) -> None:
        main = '<script src="/js/google-ads-tracking.js"></script>'
        script = (
            "GT-55NTF5CN AW-11564692382 voyagerballoons.eu "
            "tienda.voyagerballoons.eu accept_incoming decorate_forms"
        )

        findings = _audit(main, script, self.config)
        check = next(item for item in findings if item["key"] == "booking-links")

        self.assertFalse(check["ok"])
        self.assertEqual(check["evidence_url"], "https://www.voyagerballoons.eu/")


if __name__ == "__main__":
    unittest.main()
