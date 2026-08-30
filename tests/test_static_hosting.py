from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate-nginx-config.py"
SPEC = importlib.util.spec_from_file_location("generate_nginx_config", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StaticHostingConfigTests(unittest.TestCase):
    def setUp(self):
        self.redirects = MODULE.parse_redirects((ROOT / "netlify.toml").read_text(encoding="utf-8"))

    def test_all_netlify_redirects_are_represented_once(self):
        config = MODULE.render_config(self.redirects)
        expected = [item for item in self.redirects if not (item["from"] == "/*" and item["status"] == 404)]
        self.assertEqual(len(expected), config.count("# redirect:"))
        self.assertEqual(len({item["from"] for item in self.redirects}), len(self.redirects))

    def test_wildcards_preserve_the_splat(self):
        config = MODULE.render_config(self.redirects)
        self.assertIn(r"location ~ ^/producto/(.*)$", config)
        self.assertIn("return 301 https://tienda.voyagerballoons.eu/;", config)

    def test_clean_urls_custom_404_and_canonical_host_are_enabled(self):
        config = MODULE.render_config(self.redirects)
        self.assertIn("try_files $uri $uri.html $uri/index.html =404;", config)
        self.assertIn("error_page 404 /404.html;", config)
        self.assertIn("if ($host = voyagerballoons.eu)", config)
        self.assertIn("absolute_redirect off;", config)
        self.assertIn("port_in_redirect off;", config)

    def test_shared_railway_config_does_not_turn_every_service_into_a_cron(self):
        config = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))
        self.assertNotIn("deploy", config)

    def test_public_pages_use_the_official_whatsapp_api_number(self):
        public_files = [
            *ROOT.glob("*.html"),
            *ROOT.glob("*.txt"),
            *ROOT.glob("*.xml"),
            *(ROOT / "articulos").rglob("*.html"),
            *(ROOT / "en").rglob("*.html"),
            *(ROOT / "pt").rglob("*.html"),
        ]
        public_content = "\n".join(path.read_text(encoding="utf-8") for path in public_files)

        self.assertNotIn("34605087478", public_content)
        self.assertNotIn("+34 605 087 478", public_content)
        self.assertIn("https://wa.me/34614007056", public_content)
        self.assertIn("+34 614 00 70 56", public_content)

    def test_segovia_sales_pages_use_the_new_store(self):
        segovia_pages = [
            ROOT / "index.html",
            ROOT / "vuelo-en-globo-segovia.html",
            ROOT / "vuelo-en-globo-segovia-comfort.html",
            ROOT / "vuelo-en-globo-segovia-desde-madrid.html",
            ROOT / "regalar-vuelo-en-globo-segovia.html",
            ROOT / "en" / "index.html",
            ROOT / "en" / "hot-air-balloon-segovia.html",
            ROOT / "en" / "comfort-hot-air-balloon-segovia.html",
            ROOT / "en" / "hot-air-balloon-segovia-from-madrid.html",
            ROOT / "en" / "gift-hot-air-balloon-segovia.html",
        ]
        content_by_path = {
            path: path.read_text(encoding="utf-8")
            for path in segovia_pages
        }

        for path, content in content_by_path.items():
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("https://shop.voyagerballoons.eu/?add-to-cart=", content)
                self.assertIn("https://tienda.voyagerballoons.eu/", content)

        self.assertIn(
            "https://tienda.voyagerballoons.eu/regalar",
            content_by_path[ROOT / "regalar-vuelo-en-globo-segovia.html"],
        )
        self.assertIn(
            "https://tienda.voyagerballoons.eu/regalar",
            content_by_path[ROOT / "en" / "gift-hot-air-balloon-segovia.html"],
        )

    def test_braganca_pages_use_the_current_portugal_site(self):
        pages = [
            ROOT / "vuelo-en-globo-braganza-portugal.html",
            ROOT / "pt" / "passeio-de-balao-braganca.html",
            ROOT / "en" / "hot-air-balloon-braganca-portugal.html",
        ]

        for path in pages:
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn("https://www.aosabordovento.net/voo-de-balao-braganca", content)
                self.assertNotIn("shop.voyagerballoons.eu", content)

    def test_public_content_does_not_link_to_wordpress_backup(self):
        public_files = [
            *ROOT.glob("*.html"),
            *ROOT.glob("*.txt"),
            *ROOT.glob("*.xml"),
            *(ROOT / "articulos").rglob("*.html"),
            *(ROOT / "en").rglob("*.html"),
            *(ROOT / "pt").rglob("*.html"),
        ]
        public_content = "\n".join(path.read_text(encoding="utf-8") for path in public_files)

        self.assertNotIn("shop.voyagerballoons.eu", public_content)

    def test_primary_navigation_stays_compact(self):
        public_pages = [
            *ROOT.glob("*.html"),
            *(ROOT / "articulos").rglob("*.html"),
            *(ROOT / "en").rglob("*.html"),
            *(ROOT / "pt").rglob("*.html"),
        ]
        navigation_pattern = re.compile(
            r'<div class="nav-links" id="primary-navigation">(.*?)</div>',
            re.DOTALL,
        )

        for path in public_pages:
            content = path.read_text(encoding="utf-8")
            match = navigation_pattern.search(content)
            if not match:
                continue
            link_count = len(re.findall(r"<a\b", match.group(1)))
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertLessEqual(link_count, 6)


if __name__ == "__main__":
    unittest.main()
