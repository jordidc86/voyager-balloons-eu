from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..config import ROOT
from ..storage import Store
from ..types import AlertSpec, CheckResult


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del config, store, run_id
    result = CheckResult(job_name="technical")
    with tempfile.TemporaryDirectory(prefix="voyager-seo-") as tmp:
        output = Path(tmp) / "technical-crawl.json"
        process = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "technical-crawl.py"),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        if not output.exists():
            raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "El crawler no generó informe")
        report = json.loads(output.read_text(encoding="utf-8"))

    broken = report.get("broken", [])
    external_broken = report.get("external_broken", [])
    schema_errors = report.get("issues", {}).get("schema_json_errors", [])
    missing_titles = report.get("issues", {}).get("missing_title", [])
    sitemap_errors = [
        item for item in report.get("sitemaps", [])
        if item.get("error") or (item.get("status") is not None and item["status"] >= 400)
    ]

    for item in broken:
        linked_from = item.get("linked_from", [])
        result.alerts.append(AlertSpec(
            dedupe_key=f"technical:broken:{item['url']}",
            severity="P0" if "shop.voyagerballoons.eu" in item["url"] else "P1",
            category="technical",
            title="Destino interno roto",
            message=f"{item['url']} devuelve {item.get('status') or item.get('error')}. Enlazado desde {len(linked_from)} página(s).",
            action="Corregir los enlaces de origen y restaurar o redirigir el destino.",
            evidence_url=item["url"], metadata={"linked_from": linked_from[:20]},
        ))
    for item in external_broken:
        result.alerts.append(AlertSpec(
            dedupe_key=f"technical:external-broken:{item['url']}", severity="P2", category="technical",
            title="Enlace externo roto",
            message=f"El destino externo devuelve HTTP {item.get('status')}.",
            action="Sustituirlo por una fuente vigente o eliminar el enlace si ya no aporta valor.",
            evidence_url=item["url"],
        ))
    for url in schema_errors:
        result.alerts.append(AlertSpec(
            dedupe_key=f"technical:schema:{url}", severity="P1", category="technical",
            title="JSON-LD inválido", message="La página contiene datos estructurados que no se pueden interpretar.",
            action="Corregir el bloque JSON-LD y validarlo antes del siguiente despliegue.", evidence_url=url,
        ))
    for url in missing_titles:
        result.alerts.append(AlertSpec(
            dedupe_key=f"technical:title:{url}", severity="P1", category="technical",
            title="Página sin título SEO", message="El crawler no ha encontrado una etiqueta title.",
            action="Añadir un título único, descriptivo y alineado con la intención de búsqueda.", evidence_url=url,
        ))
    for item in sitemap_errors:
        result.alerts.append(AlertSpec(
            dedupe_key=f"technical:sitemap:{item['url']}", severity="P0", category="technical",
            title="Sitemap no disponible", message=f"Google no puede obtener correctamente {item['url']}.",
            action="Restaurar el sitemap, comprobar robots y reenviarlo en Search Console.", evidence_url=item["url"],
        ))

    result.summary = {
        "crawler_exit_code": process.returncode,
        "sitemaps": len(report.get("sitemaps", [])),
        "sitemap_pages": report.get("sitemap_page_count", 0),
        "pages": report.get("page_count", 0),
        "html_pages": report.get("html_page_count", 0),
        "internal_edges": report.get("internal_edge_count", 0),
        "external_targets": report.get("external_target_count", 0),
        "broken_internal": len(broken),
        "broken_external": len(external_broken),
        "schema_errors": len(schema_errors),
        "alerts": len(result.alerts),
    }
    for name in ("pages", "html_pages", "internal_edges", "external_targets", "broken_internal", "broken_external", "schema_errors"):
        result.add_metric(name, result.summary[name], source="technical")
    return result
