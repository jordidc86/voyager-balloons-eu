from __future__ import annotations

from urllib.parse import urlsplit

import requests

from ..config import Settings
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

OPPORTUNITY_AUDITS = {
    "render-blocking-insight": "Recursos que bloquean el renderizado",
    "unused-javascript": "JavaScript no utilizado",
    "unused-css-rules": "CSS no utilizado",
    "image-delivery-insight": "Entrega y compresión de imágenes",
}

FIELD_METRIC_LABELS = {
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": "TTFB",
    "FIRST_CONTENTFUL_PAINT_MS": "FCP",
    "LARGEST_CONTENTFUL_PAINT_MS": "LCP",
    "INTERACTION_TO_NEXT_PAINT": "INP",
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": "CLS",
}


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


def _performance_opportunities(audits: dict) -> list[dict]:
    opportunities = []
    for audit_id, label in OPPORTUNITY_AUDITS.items():
        audit = audits.get(audit_id, {})
        if not audit or audit.get("score") != 0:
            continue
        details = audit.get("details") or {}
        items = details.get("items") or []
        savings_ms = float(details.get("overallSavingsMs") or 0)
        savings_bytes = float(details.get("overallSavingsBytes") or 0)
        if isinstance(items, list):
            # Resource delays can overlap; summing them overstates the critical-path saving.
            savings_ms = max(
                [savings_ms]
                + [float(item.get("wastedMs") or 0) for item in items if isinstance(item, dict)]
            )
            savings_bytes = max(savings_bytes, sum(float(item.get("wastedBytes") or 0) for item in items if isinstance(item, dict)))
        resources = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict) or not item.get("url"):
                    continue
                resources.append({
                    "url": item["url"],
                    "wasted_ms": round(float(item.get("wastedMs") or 0)),
                    "wasted_kib": round(float(item.get("wastedBytes") or 0) / 1024, 1),
                })
            resources.sort(
                key=lambda item: (item["wasted_ms"], item["wasted_kib"]),
                reverse=True,
            )
        opportunities.append({
            "audit": audit_id,
            "label": label,
            "display_value": audit.get("displayValue"),
            "savings_ms": round(savings_ms),
            "savings_kib": round(savings_bytes / 1024, 1),
            "resources": resources[:5],
        })
    return sorted(
        opportunities,
        key=lambda item: (item["savings_ms"], item["savings_kib"]),
        reverse=True,
    )


def _compact_resource_label(url: str) -> str:
    parts = urlsplit(url)
    if not parts.netloc:
        return url[:80]
    path_parts = [part for part in parts.path.split("/") if part]
    path = "/".join(path_parts[-2:]) if path_parts else ""
    query = f"?{parts.query}" if parts.query else ""
    return f"{parts.netloc}/{path}{query}".rstrip("/")[:120]


def _lcp_diagnostic(audits: dict) -> dict:
    audit = audits.get("lcp-breakdown-insight", {})
    items = (audit.get("details") or {}).get("items") or []
    phases = []
    node = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "table":
            for phase in item.get("items") or []:
                if not isinstance(phase, dict) or phase.get("duration") is None:
                    continue
                phases.append({
                    "subpart": phase.get("subpart"),
                    "label": phase.get("label"),
                    "duration_ms": round(float(phase["duration"])),
                })
        elif item.get("type") == "node":
            node = {
                "selector": item.get("selector"),
                "node_label": item.get("nodeLabel"),
                "snippet": item.get("snippet"),
            }
    phases.sort(key=lambda item: item["duration_ms"], reverse=True)
    return {
        "node": node,
        "phases": phases,
        "largest_phase": phases[0] if phases else None,
    }


def _performance_action(opportunities: list[dict], lcp_diagnostic: dict) -> str:
    if not opportunities:
        return "Revisar el elemento LCP y validar el cambio con una nueva medición móvil."
    top = opportunities[0]
    targets = [
        _compact_resource_label(item["url"])
        for item in top.get("resources", [])[:3]
    ]
    target_text = f" Revisar primero: {', '.join(targets)}." if targets else ""
    largest_phase = lcp_diagnostic.get("largest_phase") or {}
    if top["audit"] == "render-blocking-insight":
        return (
            "Reducir o cargar de forma no bloqueante el CSS no esencial anterior al elemento LCP; "
            "conservar síncronos únicamente los estilos necesarios para la primera pantalla."
            + target_text
        )
    if top["audit"] == "unused-javascript":
        return "Eliminar cargas duplicadas y retrasar JavaScript no necesario para la primera interacción." + target_text
    if largest_phase.get("subpart") == "elementRenderDelay":
        return "Reducir el retraso de renderizado del elemento LCP y comprobar CSS, fuentes y trabajo de main thread." + target_text
    return "Aplicar la oportunidad de mayor ahorro y repetir Lighthouse móvil antes de ampliar el cambio." + target_text


def _failed_category_audits(categories: dict, audits: dict, category: str) -> list[dict]:
    failures = []
    for reference in categories.get(category, {}).get("auditRefs", []):
        audit = audits.get(reference.get("id"), {})
        score = audit.get("score")
        if score is None or score >= 1:
            continue
        items = (audit.get("details") or {}).get("items") or []
        failures.append({
            "id": reference.get("id"),
            "title": audit.get("title"),
            "display_value": audit.get("displayValue"),
            "nodes": [
                {
                    "selector": (item.get("node") or {}).get("selector"),
                    "snippet": (item.get("node") or {}).get("snippet"),
                }
                for item in items[:8]
                if isinstance(item, dict) and item.get("node")
            ],
        })
    return failures


def _consecutive_below(history: list[float], current: float, threshold: float) -> int:
    if current >= threshold:
        return 0
    streak = 1
    for previous in history:
        if previous >= threshold:
            break
        streak += 1
    return streak


def _lab_performance_assessment(
    history: list[float],
    current: float,
    critical: float,
    warning: float,
    confirmations: int,
) -> dict | None:
    if current >= warning:
        return None
    critical_streak = _consecutive_below(history, current, critical)
    warning_streak = _consecutive_below(history, current, warning)
    if critical_streak >= confirmations:
        return {"severity": "P1", "streak": critical_streak, "threshold": critical}
    if warning_streak >= confirmations:
        return {"severity": "P2", "streak": warning_streak, "threshold": warning}
    return None


def _field_problem_metrics(field_metrics: dict) -> list[dict]:
    problems = []
    for api_name, metric in field_metrics.items():
        category = str(metric.get("category") or "").upper()
        if api_name not in FIELD_METRIC_LABELS or category == "FAST":
            continue
        problems.append({
            "api_name": api_name,
            "label": FIELD_METRIC_LABELS[api_name],
            "category": category,
            "percentile": metric.get("percentile"),
        })
    return problems


def _format_field_problem(item: dict) -> str:
    value = item.get("percentile")
    if value is None:
        formatted = "sin percentil"
    elif item["label"] == "CLS":
        formatted = f"{float(value) / 100:.3f}"
    else:
        formatted = f"{float(value) / 1000:.2f}s"
    category = "lento" if item["category"] == "SLOW" else "necesita mejora"
    return f"{item['label']} {formatted} ({category})"


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    del run_id
    result = CheckResult(job_name="pagespeed")
    if not settings.pagespeed_api_key:
        result.status = "skipped"
        result.summary = {"reason": "PAGESPEED_API_KEY no configurado"}
        return result

    thresholds = config["thresholds"]
    lab_confirmations = int(thresholds.get("pagespeed_lab_confirmations", 2))
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
            performance_opportunities = _performance_opportunities(audits)
            lcp_diagnostic = _lcp_diagnostic(audits)
            failed_seo_audits = _failed_category_audits(categories, audits, "seo")
            dimensions = {"url": page["url"], "strategy": strategy}
            performance_history = store.metric_history(
                "score_performance",
                "pagespeed",
                dimensions,
                limit=max(0, lab_confirmations - 1),
            )
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
                "EXPERIMENTAL_TIME_TO_FIRST_BYTE": "field_ttfb_ms",
                "FIRST_CONTENTFUL_PAINT_MS": "field_fcp_ms",
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
            lab_assessment = _lab_performance_assessment(
                performance_history,
                performance,
                float(thresholds["performance_score_critical"]),
                float(thresholds["performance_score_warning"]),
                lab_confirmations,
            )
            if lab_assessment:
                top_opportunity = performance_opportunities[0]["label"] if performance_opportunities else None
                largest_lcp_phase = lcp_diagnostic.get("largest_phase") or {}
                phase_summary = (
                    f" La fase dominante del LCP es {largest_lcp_phase.get('label')} "
                    f"({largest_lcp_phase.get('duration_ms') / 1000:.2f}s)."
                    if largest_lcp_phase.get("duration_ms") is not None else ""
                )
                result.alerts.append(AlertSpec(
                    dedupe_key=f"pagespeed:performance:{strategy}:{page['url']}", severity=lab_assessment["severity"], category="pagespeed",
                    title=f"Rendimiento {strategy} bajo en {page['name']}",
                    message=(
                        f"Lighthouse Performance {performance}/100; LCP {lcp_ms / 1000:.2f}s; CLS {cls:.3f}; "
                        f"resultado degradado durante {lab_assessment['streak']} ejecuciones consecutivas."
                        + (f" Principal oportunidad detectada: {top_opportunity}." if top_opportunity else "")
                        + phase_summary
                    ),
                    action=_performance_action(performance_opportunities, lcp_diagnostic),
                    evidence_url=f"https://pagespeed.web.dev/analysis?url={page['url']}",
                    metadata={
                        "scores": scores,
                        "lcp_ms": lcp_ms,
                        "cls": cls,
                        "confirmation_streak": lab_assessment["streak"],
                        "performance_opportunities": performance_opportunities,
                        "lcp_diagnostic": lcp_diagnostic,
                    },
                ))
            if strategy == "mobile" and scores.get("seo", 100) < 100:
                result.alerts.append(AlertSpec(
                    dedupe_key=f"pagespeed:seo:{page['url']}",
                    severity="P2",
                    category="pagespeed",
                    title=f"Auditoría SEO incompleta en {page['name']}",
                    message=(
                        f"Lighthouse SEO {scores.get('seo', 0)}/100; "
                        f"fallan {len(failed_seo_audits)} comprobaciones identificables."
                    ),
                    action="Corregir primero los elementos concretos indicados y repetir Lighthouse en móvil.",
                    evidence_url=f"https://pagespeed.web.dev/analysis?url={page['url']}",
                    metadata={"scores": scores, "failed_audits": failed_seo_audits},
                ))
            if field.get("overall_category") == "SLOW" and field_key not in field_alerts_seen:
                is_origin = field_scope == "origin"
                target_label = urlsplit(field_target).netloc if is_origin else page["name"]
                field_problems = _field_problem_metrics(field_metrics)
                problem_summary = ", ".join(_format_field_problem(item) for item in field_problems)
                ttfb_slow = any(
                    item["api_name"] == "EXPERIMENTAL_TIME_TO_FIRST_BYTE" and item["category"] == "SLOW"
                    for item in field_problems
                )
                if ttfb_slow:
                    field_action = (
                        "Priorizar servidor, caché fría y respuesta inicial compartida por toda la tienda; "
                        "comparar caché HIT/MISS y observar la tendencia de CrUX durante 28 días."
                    )
                elif is_origin:
                    field_action = (
                        "Priorizar el recurso y la fase de renderizado degradados; "
                        "observar la tendencia de CrUX durante 28 días."
                    )
                else:
                    field_action = (
                        "Priorizar la métrica de campo degradada y validar el cambio sobre usuarios reales, "
                        "especialmente en móvil."
                    )
                result.alerts.append(AlertSpec(
                    dedupe_key=f"pagespeed:crux:{field_scope}:{strategy}:{field_target}",
                    severity="P1" if page.get("severity") == "P0" else "P2",
                    category="pagespeed",
                    title=f"Experiencia real lenta en {target_label}",
                    message=(
                        "CrUX (ventana móvil de 28 días) clasifica el origen completo como lento; "
                        "no permite atribuir el problema a una ficha concreta. "
                        + (f"Métricas degradadas: {problem_summary}." if problem_summary else "")
                        if is_origin else
                        "CrUX (ventana móvil de 28 días) clasifica esta URL como lenta. "
                        + (f"Métricas degradadas: {problem_summary}." if problem_summary else "")
                    ),
                    action=field_action,
                    evidence_url=f"https://pagespeed.web.dev/analysis?url={page['url']}",
                    metadata={
                        "overall_category": field.get("overall_category"),
                        "scope": field_scope,
                        "field_id": field.get("id"),
                        "metrics": field_metrics,
                        "problem_metrics": field_problems,
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
