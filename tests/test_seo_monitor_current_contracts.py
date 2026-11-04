import json
import unittest
from pathlib import Path
from unittest.mock import patch
from seo_monitor.checks import commerce
from tests.test_seo_monitor_commerce import FakeResponse

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/seo-monitor.json').read_text())

class CurrentContracts(unittest.TestCase):
    def probes(self):
        return [p for p in CONFIG['commerce_probes'] if p['name'] in ('Reserva Classic', 'Reserva Comfort', 'Braganca Ao Sabor')]

    def test_current_content_accepted(self):
        for p in self.probes():
            with self.subTest(probe=p['name']), patch('seo_monitor.checks.commerce.requests.get', return_value=FakeResponse(text='<meta name="robots" content="noindex"><main>' + ' '.join(p['expected_text']) + '</main>')):
                self.assertEqual(commerce.test_probe(p, 5)[1], [])

    def test_each_required_content_still_enforced(self):
        for p in self.probes():
            for required in p['expected_text']:
                text = ' '.join(t for t in p['expected_text'] if t != required)
                with self.subTest(probe=p['name'], missing=required), patch('seo_monitor.checks.commerce.requests.get', return_value=FakeResponse(text='<meta name="robots" content="noindex">' + text)):
                    self.assertTrue(commerce.test_probe(p, 5)[1])

    def test_http_failure_still_alerts(self):
        for p in self.probes():
            with patch('seo_monitor.checks.commerce.requests.get', return_value=FakeResponse(status_code=500)):
                self.assertTrue(commerce.test_probe(p, 5)[1])

    def test_current_prices_and_heading_are_explicit(self):
        probes = {p['name']: p for p in self.probes()}
        for name, price in [('Reserva Classic', '129'), ('Reserva Comfort', '169')]:
            self.assertEqual(probes[name]['expected_text'], ['Reserva tu vuelo en Segovia', name.split()[1], price])
            self.assertEqual(probes[name]['expected_robots'], 'noindex')
        self.assertEqual(probes['Braganca Ao Sabor']['expected_text'], ['205', 'Reservar por', 'Pagamento por transferência bancária'])
        pages = [p for p in CONFIG['strategic_pages'] if p['name'] in ('Braganza ES', 'Braganca PT', 'Braganca EN') and 'voyagerballoons' in p['url']]
        self.assertEqual(len(pages), 3)
        for p in pages:
            self.assertEqual(p['required_text'], ['205'])
