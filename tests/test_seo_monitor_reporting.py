from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from seo_monitor.reporting import render_markdown
from seo_monitor.prioritization import prioritize_alert, prioritized_alerts
from seo_monitor.models import Alert
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
            "commerce_diagnostics": {
                "complete_days": 0,
                "minimum_complete_days": 2,
                "minimum_shop_sessions": 50,
                "evaluation_ready": False,
            },
            "commerce_baseline_diagnostics": {
                "shop_sessions": 1131,
                "shop_direct_share_percent": 18.3,
                "purchases": 2,
                "purchase_revenue": 480,
            },
        })
        self.save("backlink_gap", {
            "profile_domains": 18,
            "profile_dofollow_domains": 11,
            "profile_new_domains": 1,
            "profile_confirmed_lost": 0,
        })

        report = render_markdown(self.store)

        self.assertIn("URLs estratégicas disponibles: 14/14", report)
        self.assertIn("Flujos de compra correctos: 5/5", report)
        self.assertIn("80 clics, 4000 impresiones, CTR 2.0%", report)
        self.assertIn("64 sesiones, 7 eventos clave, 845 € atribuidos", report)
        self.assertIn("Embudo GA4 post-reparación: en calentamiento", report)
        self.assertIn("se evaluará al alcanzar 2 días y 50 sesiones", report)
        self.assertIn("Histórico tienda (28 días): 2 compras y 480 €", report)
        self.assertIn("Atribución tienda (28 días): 1131 sesiones", report)
        self.assertIn("Backlinks: 18 dominios detectados, 11 con enlaces dofollow; 1 nuevos y 0 pérdidas", report)
        self.assertIn("Consulta `vuelo en globo segovia`", report)
        self.assertIn("brecha estimada 18 clics", report)
        self.assertIn("crecimiento de reservas", report)
        self.assertIn("El score ordena el trabajo", report)
        self.assertIn("hasta 18.0 clics orgánicos adicionales", report)

    def test_legacy_ga4_warmup_summary_never_renders_missing_requirements(self) -> None:
        self.save("ga4", {
            "commerce_diagnostics": {
                "complete_days": 1,
                "evaluation_ready": False,
            },
        })

        report = render_markdown(self.store)

        self.assertIn("completar el periodo mínimo configurado", report)
        self.assertNotIn("sin datos días", report)

    def test_dynamic_keyword_evidence_does_not_render_missing_values(self) -> None:
        self.save("gsc", {}, alerts=[AlertSpec(
            dedupe_key="gsc:new-commercial-keywords",
            severity="P2",
            category="gsc",
            title="Nuevas consultas",
            message="Se han activado consultas.",
            action="Revisarlas.",
            metadata={"queries": [{
                "query": "viaje en globo segovia",
                "position": 13.903,
                "impressions": 498,
                "ctr": 0,
            }]},
        )])

        report = render_markdown(self.store)

        self.assertIn("posición 13.9", report)
        self.assertIn("CTR 0.0%", report)
        self.assertNotIn("None", report)

    def test_commerce_failure_outranks_ctr_opportunity_and_pagespeed(self) -> None:
        commerce = Alert(
            dedupe_key="commerce:test", severity="P0", category="commerce",
            title="Checkout roto", message="No se puede completar la compra.",
            action="Corregir checkout.", metadata_json="{}", status="open",
        )
        ctr = Alert(
            dedupe_key="gsc:test", severity="P1", category="gsc",
            title="Oportunidad CTR", message="Hay impresiones sin clics.",
            action="Mejorar snippet.",
            metadata_json='{"queries":[{"estimated_click_gap":12}]}', status="open",
        )
        pagespeed = Alert(
            dedupe_key="pagespeed:test", severity="P1", category="pagespeed",
            title="Origen lento", message="CrUX clasifica la tienda como lenta.",
            action="Optimizar recursos.", metadata_json="{}", status="open",
        )

        ordered = prioritized_alerts([pagespeed, ctr, commerce])

        self.assertEqual(ordered[0][0].category, "commerce")
        self.assertGreater(ordered[1][1].score, ordered[2][1].score)
        self.assertLessEqual(prioritize_alert(commerce).score, 100)

    def test_destination_is_inferred_from_alert_context(self) -> None:
        alert = Alert(
            dedupe_key="indexing:braganca", severity="P2", category="indexing",
            title="Bragança pendiente", message="Google aún no reconoce la landing.",
            action="Mantener enlaces internos.", metadata_json="{}", status="open",
        )

        self.assertEqual(prioritize_alert(alert).destination, "Bragança")


if __name__ == "__main__":
    unittest.main()
