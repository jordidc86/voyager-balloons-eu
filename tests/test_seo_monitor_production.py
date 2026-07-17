from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductionContractTests(unittest.TestCase):
    def test_container_includes_every_runtime_used_by_checks(self) -> None:
        dockerfile = (ROOT / "Dockerfile.seo-monitor").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn("nodejs", dockerfile)
        self.assertIn("requirements-seo-monitor.txt", dockerfile)
        self.assertIn('["python", "-m", "seo_monitor", "tick"]', dockerfile)

    def test_python_dependencies_are_exactly_pinned(self) -> None:
        lines = [
            line.strip()
            for line in (ROOT / "requirements-seo-monitor.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(lines)
        self.assertTrue(all("==" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
