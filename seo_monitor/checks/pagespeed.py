from __future__ import annotations

from urllib.parse import urlsplit

import requests

from ..config import Settings
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


def _field_scope(page_url: str, field_id: str | None) -> tuple[str, str]:
    page_origin = _origin(page_url)
    if not field_id:
        return "unknown", page_url
    normalized_id = field_id.rstrip("/")
    if normalized_id == page_origin:
        return "origin", page_origin
    return "url", field_id


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="pagespeed")
    if not settings.pagespeed_api_key:
        result.status = "skipped"
        result.summary = {"reason": "PAGESPEED_API_KEY no configurado"}
        return result

    thresholds = config["thresholds"]
    monitored_names = {
        "Home ES",
        "Landing Segovia",
        "Comfort Segovia",
        "Madrid",
        "Braganza ES",
        "Braganca PT",
        "Segovia EN",
        "Shop home",
        "Producto Comfort",
        "Producto Braganca",
    }
    pages = [page for page in config["strategic_pages"] if page["name"] in monitored_names]
    failures = []
    completed_tests = 0
    field_metrics_seen: set[tuple[str, str]] = set()
    field_alerts_seen: set[tuple[str, str]] = set()
    for page in pages:
        for strategy in ("mobile", "desktop"):
            try:
                response = requests.get(ENDPOINT, params={
                    "url": page["url"],
                    "strategy": strategy,
                    "category": ["performance", "accessibility", "seo", "best-practices"],
                    "key": settings.pagespeed_api_key,
                }, timeout=120)
                response.raise_for_status()
                payload = response.json()
                data = payload["lighthouseResult"]
            except Exception as exc:
                failures.append({"url": page["url"], "strategy": strategy, "error": str(exc)})
                continue

            categories = data.get("categories", {})
            scores = {name: round(details.get("score", 0) * 100) for name, details in categories.items()}
            audits = data.get("audits", {})
            lcp_ms = float(audits.get("largest-contentful-paint", {}).get("numericValue", 0))
            cls = float(audits.get("cumulative-layout-shift", {}).get("numericValue", 0))
            dimensions = {"url": page["url"], "strategy": strategy}
            for name, score in scores.items():
                result.add_metric(f"score_{name}", score, source="pagespeed", dimensions=dimensions)
            result.add_metric("lcp_ms", lcp_ms, source="pagespeed", dimensions=dimensions)
            result.add_metric("cls", cls, source="pagespeed", dimensions=dimensions)
            completed_tests += 1

            field = payload.get("loadingExperience", {})
            field_metrics = field.get("metrics", {})
            field_scope, field_target = _field_scope(page["url"], field.get("id"))
            field_key = (strategy, field_target)
            field_names = {
                "LARGEST_CONTENTFUL_PAINT_MS": "field_lcp_ms",
                "INTERACTION_TO_NEXT_PAINT": "field_inp_ms",
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": "field_cls_score",
            }
            if field_key not in field_metrics_seen:
                field_dimensions = {"url": field_target, "strategy": strategy, "scope": field_scope}
                for api_name, metric_name in field_names.items():
                    metric = field_metrics.get(api_name, {})
                    if metric.get("percentile") is not None:
                        result.add_metric(metric_name, float(metric["percentile"]), source="crux", dimensions=field_dimensions)
                field_metrics_seen.add(field_key)

            performance = scores.get("performance", 0)
            if performance < thresholds["performance_score_critical"]:
                severity = "P1"
            elif performance < thresholds["performance_score_warning"]:
                severity = "P2"
            else:
                severity = None
            if severity:
                result.alerts.append(AlertSpec(
                    dedupe_key=f"pagespeed:performance:{strategy}:{page['url']}", severity=severity, category="pagespeed",
                    title=f"Rendimiento {strategy} bajo en {page['name']}",
                    message=f"Lighthouse Performance {performance}/100; LCP {lcp_ms / 1000:.2f}s; CLS {cls:.3f}.",
                    action="Revisar el elemento LCP, CSS/fuentes bloqueantes, imágenes y JavaScript; validar después con datos de campo.",
                    evidence_url=f"https://pagespeed.web.dev/analysis?url={page['url']}", metadata=scores,
                ))
            if field.get("overall_category") == "SLOW" and field_key not in field_alerts_seen:
                is_origin = field_scope == "origin"
                target_label = urlsplit(field_target).netloc if is_origin else page["name"]
                result.alerts.append(AlertSpec(
                    dedupe_key=f"pagespeed:crux:{field_scope}:{strategy}:{field_target}",
                    severity="P1" if page.get("severity") == "P0" else "P2",
                    category="pagespeed",
                    title=f"Experiencia real lenta en {target_label}",
                    message=(
                        "Los datos de campo de Chrome clasifican el origen completo como lento; "
                        "no permiten atribuir el problema a una ficha concreta."
                        if is_origin else
                        "Los datos de campo de Chrome clasifican esta URL como lenta."
                    ),
                    action=(
                        "Priorizar TTFB, caché, tema, plugins y recursos compartidos por toda la tienda; "
                        "usar Lighthouse por URL para localizar diferencias concretas."
                        if is_origin else
                        "Priorizar la métrica de campo degradada y validar el cambio sobre usuarios reales, especialmente en móvil."
                    ),
                    evidence_url=f"https://pagespeed.web.dev/analysis?url={page['url']}",
                    metadata={
                        "overall_category": field.get("overall_category"),
                        "scope": field_scope,
                        "field_id": field.get("id"),
                        "metrics": field_metrics,
                    },
                ))
                field_alerts_seen.add(field_key)

    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="pagespeed:provider-failures", severity="P2", category="pagespeed",
            title="PageSpeed no pudo analizar todas las páginas", message=f"Fallaron {len(failures)} pruebas.",
            action="Revisar cuota/API y repetir únicamente las URLs fallidas.", metadata={"failures": failures[:20]},
        ))
    result.summary = {
        "pages": len(pages),
        "tests_planned": len(pages) * 2,
        "tests_completed": completed_tests,
        "failures": len(failures),
        "alerts": len(result.alerts),
    }
    return result
