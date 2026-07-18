from __future__ import annotations

import importlib.util
import json
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
        self.assertIn("return 301 https://shop.voyagerballoons.eu/producto/$1;", config)

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


if __name__ == "__main__":
    unittest.main()
