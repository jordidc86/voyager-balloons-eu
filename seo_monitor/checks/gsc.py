from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote

from ..config import Settings
from ..google_auth import authorized_session
from ..storage import Store
from ..types import AlertSpec, CheckResult


SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def _query(session, property_name: str, start: date, end: date, dimensions: list[str], row_limit: int = 25000) -> list[dict]:
    endpoint = f"https://www.googleapis.com/webmasters/v3/sites/{quote(property_name, safe='')}/searchAnalytics/query"
    response = session.post(endpoint, json={
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "dataState": "final",
        "type": "web",
    }, timeout=45)
    response.raise_for_status()
    return response.json().get("rows", [])


def _totals(rows: list[dict]) -> dict[str, float]:
    if not rows:
        return {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0}
    row = rows[0]
    return {name: float(row.get(name, 0)) for name in ("clicks", "impressions", "ctr", "position")}


def _rows_by_key(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("keys", [""])[0]): row for row in rows}


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="gsc")
    if not settings.google_service_account_json:
        result.status = "skipped"
        result.summary = {"reason": "GOOGLE_SERVICE_ACCOUNT_JSON no configurado"}
        return result

    session = authorized_session(settings.google_service_account_json, [SCOPE])
    current_end = date.today() - timedelta(days=3)
    current_start = current_end - timedelta(days=6)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)

    current = _totals(_query(session, settings.gsc_property, current_start, current_end, []))
    previous = _totals(_query(session, settings.gsc_property, previous_start, previous_end, []))
    page_rows = _query(session, settings.gsc_property, current_start, current_end, ["page"])
    query_rows = _query(session, settings.gsc_property, current_start, current_end, ["query"], row_limit=5000)
    previous_page_rows = _query(session, settings.gsc_property, previous_start, previous_end, ["page"])
    previous_query_rows = _query(session, settings.gsc_property, previous_start, previous_end, ["query"], row_limit=5000)
    country_rows = _query(session, settings.gsc_property, current_start, current_end, ["country"])
    device_rows = _query(session, settings.gsc_property, current_start, current_end, ["device"])

    for period, values in (("current_7d", current), ("previous_7d", previous)):
        for name, value in values.items():
            result.add_metric(name, value, source="gsc", dimensions={"period": period})
    for row in page_rows:
        page = row.get("keys", [""])[0]
        for name in ("clicks", "impressions", "ctr", "position"):
            result.add_metric(name, row.get(name, 0), source="gsc_page", dimensions={"page": page, "period": "current_7d"})
    for row in query_rows:
        query = row.get("keys", [""])[0]
        for name in ("clicks", "impressions", "ctr", "position"):
            result.add_metric(name, row.get(name, 0), source="gsc_query", dimensions={"query": query, "period": "current_7d"})
    for dimension, rows in (("country", country_rows), ("device", device_rows)):
        for row in rows:
            key = row.get("keys", [""])[0]
            for name in ("clicks", "impressions", "ctr", "position"):
                result.add_metric(name, row.get(name, 0), source=f"gsc_{dimension}", dimensions={dimension: key, "period": "current_7d"})

    threshold = float(config["thresholds"].get("organic_click_drop_percent", 30))
    minimum_impressions = float(config["thresholds"].get("minimum_impressions_for_alert", 50))
    if previous["clicks"] > 0 and previous["impressions"] >= minimum_impressions:
        drop = (previous["clicks"] - current["clicks"]) / previous["clicks"] * 100
        if drop >= threshold:
            result.alerts.append(AlertSpec(
                dedupe_key="gsc:organic-click-drop", severity="P1", category="gsc",
                title="Caída relevante de clics orgánicos",
                message=f"Los clics han bajado un {drop:.1f}%: {previous['clicks']:.0f} → {current['clicks']:.0f} entre periodos comparables.",
                action="Desglosar por página, consulta, país y dispositivo; comprobar posiciones, CTR, indexación y demanda estacional.",
                evidence_url="https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:voyagerballoons.eu",
                metadata={"current": current, "previous": previous},
            ))

    previous_pages = _rows_by_key(previous_page_rows)
    current_pages = _rows_by_key(page_rows)
    page_declines = []
    for page, previous_row in previous_pages.items():
        if float(previous_row.get("clicks", 0)) < 3:
            continue
        row = current_pages.get(page, {})
        previous_clicks = float(previous_row.get("clicks", 0))
        current_clicks = float(row.get("clicks", 0))
        drop = (previous_clicks - current_clicks) / previous_clicks * 100
        if drop >= threshold:
            page_declines.append({
                "page": page,
                "drop_percent": round(drop, 1),
                "previous_clicks": previous_clicks,
                "current_clicks": current_clicks,
                "current_impressions": float(row.get("impressions", 0)),
            })
    if page_declines:
        page_declines.sort(key=lambda item: item["previous_clicks"] - item["current_clicks"], reverse=True)
        result.alerts.append(AlertSpec(
            dedupe_key="gsc:page-click-declines",
            severity="P1",
            category="gsc",
            title="Páginas con pérdida relevante de clics orgánicos",
            message=f"Se detectan {len(page_declines)} páginas con una caída superior al {threshold:.0f}% frente al periodo comparable.",
            action="Priorizar las páginas con mayor pérdida absoluta; separar estacionalidad, caída de posición, CTR, indexación y cambios de SERP.",
            evidence_url="https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:voyagerballoons.eu",
            metadata={"pages": page_declines[:15]},
        ))

    opportunities = []
    for query, row in _rows_by_key(query_rows).items():
        impressions = float(row.get("impressions", 0))
        ctr = float(row.get("ctr", 0))
        position = float(row.get("position", 0))
        if impressions < minimum_impressions or not 4 <= position <= 20 or ctr >= 0.05:
            continue
        opportunities.append({
            "query": query,
            "clicks": float(row.get("clicks", 0)),
            "impressions": impressions,
            "ctr_percent": round(ctr * 100, 2),
            "position": round(position, 1),
            "estimated_click_gap": round(impressions * (0.05 - ctr), 1),
        })
    opportunities.sort(key=lambda item: item["estimated_click_gap"], reverse=True)
    if opportunities:
        result.alerts.append(AlertSpec(
            dedupe_key="gsc:ctr-opportunities",
            severity="P2",
            category="gsc",
            title="Consultas con oportunidad de CTR y posición",
            message=f"Hay {len(opportunities)} consultas con demanda suficiente, posición 4–20 y CTR inferior al 5%.",
            action="Revisar primero intención y SERP de las consultas con mayor brecha; mejorar título/snippet, contenido y enlazado solo cuando la landing sea la adecuada.",
            evidence_url="https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:voyagerballoons.eu",
            metadata={"queries": opportunities[:20]},
        ))

    previous_queries = set(_rows_by_key(previous_query_rows))
    new_queries = [
        query for query, row in _rows_by_key(query_rows).items()
        if query not in previous_queries and float(row.get("impressions", 0)) >= minimum_impressions
    ]

    result.summary = {
        "current_period": [current_start.isoformat(), current_end.isoformat()],
        "previous_period": [previous_start.isoformat(), previous_end.isoformat()],
        "current": current,
        "previous": previous,
        "pages": len(page_rows),
        "queries": len(query_rows),
        "countries": len(country_rows),
        "devices": len(device_rows),
        "page_declines": len(page_declines),
        "ctr_opportunities": len(opportunities),
        "new_queries": len(new_queries),
        "alerts": len(result.alerts),
    }
    return result
