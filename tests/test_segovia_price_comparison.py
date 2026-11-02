"""Keep the price comparison readable in raw HTML and consistent with its offers."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / 'vuelo-en-globo-segovia.html'


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def text(html):
    parser = Text()
    parser.feed(html)
    return ' '.join(' '.join(parser.parts).split())


class SegoviaPriceComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text()
        cls.block = re.search(r'<section class="section flight-price-comparison".*?</section>', cls.html, re.S)[0]
        cls.cards = {m[1]: m[0] for m in re.finditer(r'<article class="flight-price-card" id="([^"]+)".*?</article>', cls.block, re.S)}
        cls.nodes = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', cls.html, re.S)[1])['@graph']

    def test_comparison_is_available_without_javascript_or_cookie_acceptance(self):
        self.assertEqual(set(self.cards), {'classic-adventure', 'comfort', 'private-suite'})
        self.assertIn('¿Cuánto cuesta un vuelo en globo en Segovia y qué opción elegir?', text(self.block))
        self.assertNotRegex(self.block, r'<script|\bhidden\b|fade-in|slide-up')
        for card in self.cards.values():
            self.assertIn('<h3 ', card)
            self.assertIn('<a href=', card)

    def test_prices_and_units_do_not_confuse_a_person_with_a_private_balloon(self):
        self.assertIn('Desde 120 € por persona', text(self.cards['classic-adventure']))
        self.assertIn('169 € por persona', text(self.cards['comfort']))
        self.assertIn('máximo cuatro personas por compartimento', text(self.cards['comfort']))
        private = text(self.cards['private-suite'])
        self.assertIn('Desde 1.200 € precio total por globo privado', private)
        self.assertNotIn('por persona', private)
        self.assertIn('Consulta el precio final y la disponibilidad', text(self.cards['classic-adventure']))

    def test_booking_actions_keep_the_existing_product_and_consultation_routes(self):
        self.assertIn('href="https://tienda.voyagerballoons.eu/reservar?producto=classic"', self.cards['classic-adventure'])
        self.assertIn('href="https://tienda.voyagerballoons.eu/reservar?producto=comfort"', self.cards['comfort'])
        self.assertIn('href="/vuelo-en-globo-segovia-comfort"', self.cards['comfort'])
        self.assertIn('href="https://wa.me/34614007056?text=', self.cards['private-suite'])
        self.assertNotIn('tienda.voyagerballoons.eu', self.cards['private-suite'])

    def test_faq_price_answer_matches_the_structured_answer_exactly(self):
        faq = next(n for n in self.nodes if n['@type'] == 'FAQPage')
        answer = next(q for q in faq['mainEntity'] if q['name'] == '¿Cuánto cuesta un vuelo en globo en Segovia?')['acceptedAnswer']['text']
        match = re.search(r'<span>¿Cuánto cuesta un vuelo en globo en Segovia\?</span>.*?<div class="faq-answer">\s*<p>(.*?)</p>', self.html, re.S)
        self.assertEqual(text(match[1]), answer)
        for amount in ['120 € por persona', '169 € por persona', '1.200 € por globo privado']:
            self.assertIn(amount, answer)

    def test_structured_offers_keep_prices_and_explicit_units(self):
        for fragment, amount, unit in [('classic-adventure', '120', 'persona'), ('comfort', '169', 'persona'), ('private-suite', '1200', 'globo privado')]:
            node = next(n for n in self.nodes if n.get('@id', '').endswith('#' + fragment))
            offer = node['offers']
            price = offer['priceSpecification']
            self.assertEqual(price.get('price', price.get('minPrice')), amount)
            self.assertEqual(price['priceCurrency'], 'EUR')
            self.assertEqual(price['referenceQuantity']['unitText'], unit)
            self.assertEqual(price['referenceQuantity']['value'], 1)
            if fragment == 'private-suite':
                self.assertNotIn('availability', offer)
                self.assertNotIn('price', price)
                self.assertIn('por consulta', offer['description'])

    def test_existing_anchor_canonical_and_order_are_preserved(self):
        self.assertEqual(self.html.count('id="precio"'), 1)
        self.assertIn('<link rel="canonical" href="https://www.voyagerballoons.eu/vuelo-en-globo-segovia">', self.html)
        self.assertIn('<meta name="robots" content="index, follow">', self.html)
        self.assertLess(self.html.index('id="busquedas"'), self.html.index('id="precio"'))
        self.assertLess(self.html.index('id="precio"'), self.html.index('id="reserva-directa"'))
        ids = re.findall(r'\bid="([^"]+)"', self.html)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main()
