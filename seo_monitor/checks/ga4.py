from __future__ import annotations

from datetime import date, timedelta

from ..config import Settings
from ..google_auth import authorized_session
from ..storage import Store
from ..types import AlertSpec, CheckResult


SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def _report(session, property_id: str, start: date, end: date) -> dict[str, float]:
    endpoint = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    response = session.post(endpoint, json={
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "metrics": [
            {"name": "sessions"},
            {"name": "engagedSessions"},
            {"name": "keyEvents"},
            {"name": "totalRevenue"},
        ],
        "dimensionFilter": {
            "filter": {
                "fieldName": "sessionDefaultChannelGroup",
                "stringFilter": {"matchType": "EXACT", "value": "Organic Search"},
            }
        },
    }, timeout=45)
    response.raise_for_status()
    data = response.json()
    headers = [item["name"] for item in data.get("metricHeaders", [])]
    values = data.get("rows", [{}])[0].get("metricValues", []) if data.get("rows") else []
    return {name: float(value.get("value", 0)) for name, value in zip(headers, values)}


def _dimension_report(
    session,
    property_id: str,
    start: date,
    end: date,
    dimension: str,
    metrics: list[str],
    limit: int = 1000,
) -> list[dict]:
    endpoint = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    response = session.post(endpoint, json={
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": dimension}],
        "metrics": [{"name": name} for name in metrics],
        "dimensionFilter": {
            "filter": {
                "fieldName": "sessionDefaultChannelGroup",
                "stringFilter": {"matchType": "EXACT", "value": "Organic Search"},
            }
        },
        "orderBys": [{"metric": {"metricName": metrics[0]}, "desc": True}],
        "limit": limit,
    }, timeout=45)
    response.raise_for_status()
    data = response.json()
    metric_headers = [item["name"] for item in data.get("metricHeaders", [])]
    rows = []
    for row in data.get("rows", []):
        key = row.get("dimensionValues", [{}])[0].get("value", "")
        values = {
            name: float(value.get("value", 0))
            for name, value in zip(metric_headers, row.get("metricValues", []))
        }
        rows.append({dimension: key, **values})
    return rows


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="ga4")
    if not settings.google_service_account_json or not settings.ga4_property_id:
        result.status = "skipped"
        result.summary = {"reason": "Credenciales Google o GA4_PROPERTY_ID no configurados"}
        return result

    session = authorized_session(settings.google_service_account_json, [SCOPE])
    current_end = date.today() - timedelta(days=1)
    current_start = current_end - timedelta(days=6)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    current = _report(session, settings.ga4_property_id, current_start, current_end)
    previous = _report(session, settings.ga4_property_id, previous_start, previous_end)
    landing_rows = _dimension_report(
        session,
        settings.ga4_property_id,
        current_start,
        current_end,
        "landingPagePlusQueryString",
        ["sessions", "engagedSessions", "keyEvents", "totalRevenue"],
    )
    event_rows = _dimension_report(
        session,
        settings.ga4_property_id,
        current_start,
        current_end,
        "eventName",
        ["eventCount", "keyEvents", "totalRevenue"],
    )

    for period, values in (("current_7d", current), ("previous_7d", previous)):
        for name, value in values.items():
            result.add_metric(name, value, source="ga4_organic", dimensions={"period": period})
    for row in landing_rows:
        landing_page = row["landingPagePlusQueryString"]
        for name in ("sessions", "engagedSessions", "keyEvents", "totalRevenue"):
            result.add_metric(name, row.get(name, 0), source="ga4_landing", dimensions={"landing_page": landing_page})
    for row in event_rows:
        event_name = row["eventName"]
        for name in ("eventCount", "keyEvents", "totalRevenue"):
            result.add_metric(name, row.get(name, 0), source="ga4_event", dimensions={"event_name": event_name})

    threshold = float(config["thresholds"].get("organic_conversion_drop_percent", 30))
    previous_events = previous.get("keyEvents", 0)
    current_events = current.get("keyEvents", 0)
    if previous_events >= 3:
        drop = (previous_events - current_events) / previous_events * 100
        if drop >= threshold:
            result.alerts.append(AlertSpec(
                dedupe_key="ga4:organic-conversion-drop", severity="P1", category="ga4",
                title="Caída de conversiones procedentes de orgánico",
                message=f"Los eventos clave orgánicos han bajado un {drop:.1f}%: {previous_events:.0f} → {current_events:.0f}.",
                action="Separar compras, WhatsApp y llamadas; revisar páginas de entrada y flujo de compra antes de atribuirlo al SEO.",
                evidence_url="https://analytics.google.com/",
                metadata={"current": current, "previous": previous},
            ))

    result.summary = {
        "current_period": [current_start.isoformat(), current_end.isoformat()],
        "previous_period": [previous_start.isoformat(), previous_end.isoformat()],
        "current": current,
        "previous": previous,
        "landing_pages": len(landing_rows),
        "events": len(event_rows),
        "top_landing_pages": landing_rows[:10],
        "conversion_events": [
            row for row in event_rows
            if row.get("keyEvents", 0) > 0 or row.get("eventName") in {"purchase", "begin_checkout", "add_to_cart"}
        ][:20],
        "alerts": len(result.alerts),
    }
    return result
