from __future__ import annotations

import json
from datetime import datetime, timezone

from .storage import Store
from .prioritization import prioritized_alerts
from .types import SEVERITY_ORDER


JOB_LABELS = {
    "health": "Disponibilidad web",
    "commerce": "Flujos de compra",
    "gsc": "Search Console",
    "indexing": "Indexación estratégica",
    "ga4": "GA4 orgánico",
    "rank": "Posiciones orgánicas",
    "keyword_demand": "Demanda de keywords",
    "local_visibility": "Google Maps",
    "ai_visibility": "Visibilidad IA",
    "technical": "Crawl técnico",
    "tracking": "Integridad Analytics",
    "pagespeed": "PageSpeed",
    "competitors": "Competidores",
    "backlinks": "Backlinks",
    "backlink_gap": "Brecha de backlinks",
}


def _summary(raw: str) -> str:
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw or ""
    return ", ".join(f"{key}={value}" for key, value in data.items() if not isinstance(value, (dict, list)))


def _summary_dict(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _alert_evidence(raw: str) -> list[str]:
    metadata = _summary_dict(raw)
    lines = []
    for item in metadata.get("queries", [])[:5]:
        lines.append(
            f"- Consulta `{item.get('query')}` · posición {item.get('position')} · "
            f"{item.get('impressions')} impresiones · CTR {item.get('ctr_percent')}% · "
            f"brecha estimada {item.get('estimated_click_gap')} clics"
        )
    for item in metadata.get("pages", [])[:5]:
        lines.append(
            f"- Página `{item.get('page')}` · {item.get('previous_clicks')} → "
            f"{item.get('current_clicks')} clics ({item.get('drop_percent')}%)"
        )
    for item in metadata.get("opportunities", [])[:5]:
        if item.get("domain"):
            lines.append(
                f"- Dominio `{item.get('domain')}` · score {item.get('score')} · "
                f"autoridad {item.get('rank')} · competidores: {', '.join(item.get('competitors', []))}"
            )
        elif item.get("keyword"):
            position = item.get("position") or "fuera del seguimiento"
            lines.append(
                f"- Keyword `{item.get('keyword')}` · {item.get('search_volume')} búsquedas/mes · "
                f"CPC ${item.get('cpc')} · posición {position} · intención {item.get('intent') or 'sin clasificar'}"
            )
    return lines


def _age(now: datetime, observed: datetime) -> str:
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    seconds = max(0, int((now - observed).total_seconds()))
    if seconds < 3600:
        return f"hace {max(1, seconds // 60)} min"
    if seconds < 86400:
        return f"hace {seconds // 3600} h"
    return f"hace {seconds // 86400} d"


def _percent(value, scale: float = 1.0) -> str:
    if value is None:
        return "sin datos"
    return f"{round(float(value) * scale, 2)}%"


def render_markdown(store: Store) -> str:
    now = datetime.now(timezone.utc)
    alerts = sorted(store.open_alerts(), key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.category, item.title))
    prioritized = prioritized_alerts(alerts)
    runs = list(store.recent_runs(20))
    latest_runs = {job_name: store.latest_run(job_name) for job_name in JOB_LABELS}
    operational_sources = sum(1 for run in latest_runs.values() if run and run.status == "success")
    pending_sources = sum(1 for run in latest_runs.values() if run is None or run.status == "skipped")
    failed_sources = sum(1 for run in latest_runs.values() if run and run.status == "failed")
    lines = [
        "# Voyager SEO Intelligence",
        "",
        f"Generado: {now.isoformat()}",
        "",
        "## Estado ejecutivo",
        "",
        f"- Alertas abiertas: {len(alerts)}",
        f"- P0: {sum(1 for item in alerts if item.severity == 'P0')}",
        f"- P1: {sum(1 for item in alerts if item.severity == 'P1')}",
        f"- P2/P3: {sum(1 for item in alerts if item.severity in {'P2', 'P3'})}",
        f"- Fuentes operativas: {operational_sources}/{len(JOB_LABELS)}",
        f"- Fuentes pendientes de credenciales o primera ejecución: {pending_sources}",
        f"- Fuentes con fallo: {failed_sources}",
        "",
        "## Cobertura del sistema",
        "",
        "| Fuente | Estado | Última ejecución | Resultado |",
        "| --- | --- | --- | --- |",
    ]
    for job_name, label in JOB_LABELS.items():
        run = latest_runs[job_name]
        if run is None:
            lines.append(f"| {label} | pendiente | nunca | Sin datos |")
            continue
        summary = _summary(run.summary_json) or (run.error.splitlines()[-1] if run.error else "Sin resumen")
        lines.append(f"| {label} | {run.status} | {_age(now, run.started_at)} | {summary[:180]} |")

    commerce = store.latest_run("commerce")
    health = store.latest_run("health")
    commerce_summary = _summary_dict(commerce.summary_json) if commerce else {}
    health_summary = _summary_dict(health.summary_json) if health else {}
    gsc_summary = _summary_dict(latest_runs["gsc"].summary_json) if latest_runs["gsc"] else {}
    ga4_summary = _summary_dict(latest_runs["ga4"].summary_json) if latest_runs["ga4"] else {}
    rank_summary = _summary_dict(latest_runs["rank"].summary_json) if latest_runs["rank"] else {}
    local_summary = _summary_dict(latest_runs["local_visibility"].summary_json) if latest_runs["local_visibility"] else {}
    ai_summary = _summary_dict(latest_runs["ai_visibility"].summary_json) if latest_runs["ai_visibility"] else {}
    demand_summary = _summary_dict(latest_runs["keyword_demand"].summary_json) if latest_runs["keyword_demand"] else {}
    gsc_current = gsc_summary.get("current", {})
    ga4_current = ga4_summary.get("current", {})
    lines.extend([
        "",
        "## Protección de reservas directas",
        "",
        f"- URLs estratégicas disponibles: {health_summary.get('healthy_2xx', 'sin datos')}/{health_summary.get('pages_checked', 'sin datos')}",
        f"- Flujos de compra correctos: {commerce_summary.get('successful_flows', 'sin datos')}/{commerce_summary.get('products_tested', 'sin datos')}",
        "",
        "## Rendimiento orgánico y visibilidad",
        "",
        f"- Search Console (7 días): {gsc_current.get('clicks', 'sin datos')} clics, {gsc_current.get('impressions', 'sin datos')} impresiones, CTR {_percent(gsc_current.get('ctr'), 100)}.",
        f"- GA4 orgánico (7 días): {ga4_current.get('sessions', 'sin datos')} sesiones, {ga4_current.get('keyEvents', 'sin datos')} eventos clave, {ga4_current.get('totalRevenue', 'sin datos')} € atribuidos.",
        f"- Rankings: {rank_summary.get('found_top_10', 'sin datos')}/{rank_summary.get('keywords_checked', 'sin datos')} keywords comprobadas en top 10.",
        f"- Demanda: datos disponibles para {demand_summary.get('keywords_with_data', 'sin datos')}/{demand_summary.get('keywords_inventory', 'sin datos')} keywords; {demand_summary.get('opportunities', 'sin datos')} oportunidades fuera del top 10.",
        f"- Google Maps: {local_summary.get('found_top_3', 'sin datos')}/{local_summary.get('checks', 'sin datos')} consultas en top 3.",
        f"- IA: menciones {_percent(ai_summary.get('mention_share_percent'))}, citas {_percent(ai_summary.get('citation_share_percent'))}.",
        "",
        "## Acciones priorizadas",
        "",
    ])
    if not alerts:
        lines.append("No hay alertas abiertas.")
    else:
        lines.extend([
            "El score ordena el trabajo por riesgo, cercanía a la reserva y evidencia disponible; no representa ingresos garantizados.",
            "",
            "| Score | Horizonte | Impacto | Destino | Acción |",
            "| ---: | --- | --- | --- | --- |",
        ])
        for item, priority in prioritized[:5]:
            lines.append(
                f"| {priority.score}/100 | {priority.horizon} | {priority.impact} | "
                f"{priority.destination} | {item.title} |"
            )
        lines.extend(["", "## Detalle de acciones", ""])
    for item, priority in prioritized:
        lines.extend([
            f"### {priority.score}/100 · {item.severity} · {item.title}",
            "",
            item.message,
            "",
            f"**Impacto:** {priority.impact} · **Horizonte:** {priority.horizon} · "
            f"**Esfuerzo:** {priority.effort} · **Destino:** {priority.destination}",
            "",
            f"**Potencial:** {priority.upside}",
            "",
            f"**Criterio:** {priority.rationale}",
            "",
            f"**Acción:** {item.action}",
            *( [f"**Evidencia:** {item.evidence_url}"] if item.evidence_url else [] ),
            *_alert_evidence(item.metadata_json),
            "",
        ])
    lines.extend(["", "## Ejecuciones recientes", ""])
    for run in runs:
        lines.append(f"- `{run.job_name}` · {run.status} · {run.started_at.isoformat()} · {_summary(run.summary_json)}")
    return "\n".join(lines).rstrip() + "\n"
