"""Guard the commercial facts explicitly confirmed by the owner on 2 Nov 2026."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.in_data = False

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.blocks.append("")
            self.in_data = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_data = False

    def handle_data(self, data):
        if self.in_data:
            self.blocks[-1] += data


def public_files():
    return [*ROOT.glob("*.html"), *ROOT.glob("llms*.txt"),
            *(ROOT / "articulos").rglob("*.html"),
            *(ROOT / "en").rglob("*.html"), *(ROOT / "pt").rglob("*.html")]


def prices(node):
    if isinstance(node, dict):
        if "price" in node:
            yield str(node["price"])
        for value in node.values():
            yield from prices(value)
    elif isinstance(node, list):
        for value in node:
            yield from prices(value)


class PublicCommercialTermsTests(unittest.TestCase):
    def test_braganca_offers_have_the_confirmed_price_in_all_languages(self):
        for name in ["vuelo-en-globo-braganza-portugal.html",
                     "en/hot-air-balloon-braganca-portugal.html", "pt/passeio-de-balao-braganca.html"]:
            page = PublicPage()
            page.feed((ROOT / name).read_text())
            values = [value for block in page.blocks for value in prices(json.loads(block))]
            with self.subTest(page=name):
                self.assertTrue(values)
                self.assertEqual(set(values), {"205"})

    def test_obsolete_prices_and_unconditional_refund_denials_do_not_return(self):
        pattern = re.compile(r"195\s*(?:€|EUR|euros)|€\s*195|\bnot refundable\b|\bnon-refundable\b|no (?:son|es) reembolsables?", re.I)
        for path in public_files():
            with self.subTest(page=path.relative_to(ROOT)):
                self.assertIsNone(pattern.search(path.read_text()))

    def test_general_policy_includes_dated_bookings_and_all_public_jsonld_is_valid(self):
        policy = (ROOT / "legales.html").read_text()
        self.assertIn("15 días naturales siguientes a la compra", policy)
        self.assertIn("Se aplica a todas las compras, incluidas las reservas con fecha", policy)
        self.assertIn("siempre que el vuelo no se haya realizado", policy)
        for path in public_files():
            page = PublicPage()
            page.feed(path.read_text())
            for block in page.blocks:
                with self.subTest(page=path.relative_to(ROOT)):
                    json.loads(block)


if __name__ == "__main__":
    unittest.main()
