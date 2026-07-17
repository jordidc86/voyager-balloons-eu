from __future__ import annotations

import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from seo_monitor.checks import commerce
from seo_monitor.types import AlertSpec


class CommerceTests(unittest.TestCase):
    def test_cart_product_is_detected_by_id_across_translated_names(self) -> None:
        soup = BeautifulSoup(
            '<a class="remove" data-product_id="4174"></a>'
            '<a href="https://shop.voyagerballoons.eu/producto/vuelo-en-globo-braganza-portugal/">'
            'Passeio de Balão em Bragança</a>',
            "html.parser",
        )
        product = {
            "url": "https://shop.voyagerballoons.eu/producto/vuelo-en-globo-braganza-portugal/",
            "expected_text": "Braganza",
        }
        self.assertTrue(commerce._cart_contains_product(soup, "4174", product))

    @patch("seo_monitor.checks.commerce.test_product")
    def test_summary_never_counts_an_alerted_flow_as_successful(self, test_product) -> None:
        product = {"name": "Braganca", "url": "https://example.test", "expected_text": "Braganca"}
        alert = AlertSpec(
            dedupe_key="commerce:cart:braganca",
            severity="P0",
            category="commerce",
            title="Broken",
            message="Broken",
            action="Fix",
        )
        test_product.return_value = ({
            "product": "Braganca",
            "checkout_form": True,
            "payment_section": True,
            "flow_ok": False,
        }, [alert])

        result = commerce.run(
            {"thresholds": {}, "commerce_products": [product]},
            store=None,
            run_id=1,
        )

        self.assertEqual(result.summary["successful_flows"], 0)
        self.assertEqual(result.summary["alerts"], 1)


if __name__ == "__main__":
    unittest.main()
