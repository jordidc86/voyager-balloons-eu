from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seo_monitor.reporting import render_markdown
from seo_monitor.storage import Store
from seo_monitor.types import AlertSpec, CheckResult


class ReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(f"sqlite:///{Path(self.tmp.name) / 'monitor.db'}")
        self.store.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def save(self, job_name: str, summary: dict, alerts=None) -> None:
        run_id = self.store.start_job(job_name)
        self.store.save_result(
            run_id,
            CheckResult(job_name=job_name, summary=summary, alerts=alerts or []),
        )

    def test_report_includes_business_metrics_and_action_evidence(self) -> None:
        self.save("health", {"healthy_2xx": 14, "pages_checked": 14})
        self.save("commerce", {"successful_flows": 5, "products_tested": 5})
        self.save("gsc", {
            "current": {"clicks": 80, "impressions": 4000, "ctr": 0.02},
        }, alerts=[AlertSpec(
            dedupe_key="gsc:ctr-opportunity",
            severity="P1",
            category="gsc",
            title="Oportunidad de CTR",
            message="Una consulta importante recibe impresiones sin suficientes clics.",
            action="Mejorar el title y la descripción de la landing.",
            metadata={"queries": [{
                "query": "vuelo en globo segovia",
                "position": 4.2,
                "impressions": 900,
                "ctr_percent": 1.1,
                "estimated_click_gap": 18,
            }]},
        )])
        self.save("ga4", {
            "current": {"sessions": 64, "keyEvents": 7, "totalRevenue": 845},
        })

        report = render_markdown(self.store)

        self.assertIn("URLs estratégicas disponibles: 14/14", report)
        self.assertIn("Flujos de compra correctos: 5/5", report)
        self.assertIn("80 clics, 4000 impresiones, CTR 2.0%", report)
        self.assertIn("64 sesiones, 7 eventos clave, 845 € atribuidos", report)
        self.assertIn("Consulta `vuelo en globo segovia`", report)
        self.assertIn("brecha estimada 18 clics", report)


if __name__ == "__main__":
    unittest.main()
