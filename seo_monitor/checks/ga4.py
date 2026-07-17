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
    return _multi_dimension_report(
        session,
        property_id,
        start,
        end,
        [dimension],
        metrics,
        dimension_filter={
            "filter": {
                "fieldName": "sessionDefaultChannelGroup",
                "stringFilter": {"matchType": "EXACT", "value": "Organic Search"},
            }
        },
        limit=limit,
    )


def _multi_dimension_report(
    session,
    property_id: str,
    start: date,
    end: date,
    dimensions: list[str],
    metrics: list[str],
    dimension_filter: dict | None = None,
    limit: int = 1000,
) -> list[dict]:
    endpoint = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": name} for name in dimensions],
        "metrics": [{"name": name} for name in metrics],
        "orderBys": [{"metric": {"metricName": metrics[0]}, "desc": True}],
        "limit": limit,
    }
    if dimension_filter:
        body["dimensionFilter"] = dimension_filter
    response = session.post(endpoint, json=body, timeout=45)
    response.raise_for_status()
    data = response.json()
    dimension_headers = [item["name"] for item in data.get("dimensionHeaders", [])] or dimensions
    metric_headers = [item["name"] for item in data.get("metricHeaders", [])]
    rows = []
    for row in data.get("rows", []):
        dimension_values = {
            name: value.get("value", "")
            for name, value in zip(dimension_headers, row.get("dimensionValues", []))
        }
        values = {
            name: float(value.get("value", 0))
            for name, value in zip(metric_headers, row.get("metricValues", []))
        }
        rows.append({**dimension_values, **values})
    return rows


def _commerce_diagnostics(
    commerce_rows: list[dict],
    channel_host_rows: list[dict],
    shop_domain: str,
    minimum_shop_sessions: float = 100,
    evaluation_ready: bool = True,
) -> dict:
    event_totals: dict[str, dict[str, float]] = {}
    for row in commerce_rows:
        event_name = row.get("eventName", "")
        totals = event_totals.setdefault(event_name, {"eventCount": 0, "keyEvents": 0, "totalRevenue": 0})
        for metric in totals:
            totals[metric] += float(row.get(metric, 0) or 0)

    shop_rows = [row for row in channel_host_rows if row.get("hostName") == shop_domain]
    shop_sessions = sum(float(row.get("sessions", 0) or 0) for row in shop_rows)
    direct_sessions = sum(
        float(row.get("sessions", 0) or 0)
        for row in shop_rows
        if row.get("sessionDefaultChannelGroup") == "Direct"
    )
    technical_sessions = sum(
        float(row.get("sessions", 0) or 0)
        for row in channel_host_rows
        if row.get("hostName") in {"localhost", "127.0.0.1"}
    )
    purchases = event_totals.get("purchase", {})
    add_to_cart = event_totals.get("add_to_cart", {}).get("eventCount", 0)
    begin_checkout = event_totals.get("begin_checkout", {}).get("eventCount", 0)
    enough_shop_traffic = shop_sessions >= minimum_shop_sessions
    return {
        "shop_sessions": shop_sessions,
        "shop_direct_sessions": direct_sessions,
        "shop_direct_share_percent": round(direct_sessions / shop_sessions * 100, 1) if shop_sessions else 0,
        "technical_sessions": technical_sessions,
        "add_to_cart": add_to_cart,
        "begin_checkout": begin_checkout,
        "purchases": purchases.get("eventCount", 0),
        "purchase_revenue": purchases.get("totalRevenue", 0),
        "minimum_shop_sessions": minimum_shop_sessions,
        "evaluation_ready": evaluation_ready and enough_shop_traffic,
        "add_to_cart_missing": evaluation_ready and enough_shop_traffic and add_to_cart == 0,
        "begin_checkout_missing": evaluation_ready and enough_shop_traffic and begin_checkout == 0,
        "funnel_missing": evaluation_ready and enough_shop_traffic and (add_to_cart == 0 or begin_checkout == 0),
    }


def _funnel_window(config: dict, current_end: date, default_start: date) -> tuple[date, int, bool]:
    configured = config.get("tracking", {}).get("funnel_tracking_start_date")
    try:
        start = max(default_start, date.fromisoformat(str(configured))) if configured else default_start
    except ValueError:
        start = default_start
    complete_days = max(0, (current_end - start).days + 1)
    minimum_days = int(config.get("thresholds", {}).get("ga4_funnel_minimum_complete_days", 2))
    return start, complete_days, complete_days >= minimum_days


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
    commerce_start = current_end - timedelta(days=27)
    commerce_rows = _multi_dimension_report(
        session,
        settings.ga4_property_id,
        commerce_start,
        current_end,
        ["eventName", "hostName"],
        ["eventCount", "keyEvents", "totalRevenue"],
        dimension_filter={
            "filter": {
                "fieldName": "eventName",
                "inListFilter": {
                    "values": ["purchase", "begin_checkout", "add_to_cart"],
                },
            }
        },
    )
    channel_host_rows = _multi_dimension_report(
        session,
        settings.ga4_property_id,
        commerce_start,
        current_end,
        ["sessionDefaultChannelGroup", "hostName"],
        ["sessions", "keyEvents", "totalRevenue"],
    )
    historical_diagnostics = _commerce_diagnostics(
        commerce_rows,
        channel_host_rows,
        "shop.voyagerballoons.eu",
        evaluation_ready=False,
    )
    funnel_start, funnel_complete_days, funnel_days_ready = _funnel_window(config, current_end, commerce_start)
    funnel_rows: list[dict] = []
    funnel_channel_host_rows: list[dict] = []
    if funnel_start <= current_end:
        funnel_rows = _multi_dimension_report(
            session,
            settings.ga4_property_id,
            funnel_start,
            current_end,
            ["eventName", "hostName"],
            ["eventCount", "keyEvents", "totalRevenue"],
            dimension_filter={
                "filter": {
                    "fieldName": "eventName",
                    "inListFilter": {
                        "values": ["purchase", "begin_checkout", "add_to_cart"],
                    },
                }
            },
        )
        funnel_channel_host_rows = _multi_dimension_report(
            session,
            settings.ga4_property_id,
            funnel_start,
            current_end,
            ["sessionDefaultChannelGroup", "hostName"],
            ["sessions", "keyEvents", "totalRevenue"],
        )
    minimum_funnel_sessions = float(
        config.get("thresholds", {}).get("ga4_funnel_minimum_shop_sessions", 50)
    )
    diagnostics = _commerce_diagnostics(
        funnel_rows,
        funnel_channel_host_rows,
        "shop.voyagerballoons.eu",
        minimum_shop_sessions=minimum_funnel_sessions,
        evaluation_ready=funnel_days_ready,
    )
    diagnostics["complete_days"] = funnel_complete_days

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
    for row in commerce_rows:
        for name in ("eventCount", "keyEvents", "totalRevenue"):
            result.add_metric(
                name,
                row.get(name, 0),
                source="ga4_commerce_28d",
                dimensions={"event_name": row.get("eventName", ""), "host_name": row.get("hostName", "")},
            )
    for row in channel_host_rows:
        result.add_metric(
            "sessions",
            row.get("sessions", 0),
            source="ga4_channel_host_28d",
            dimensions={
                "channel": row.get("sessionDefaultChannelGroup", ""),
                "host_name": row.get("hostName", ""),
            },
        )
    for row in funnel_rows:
        for name in ("eventCount", "keyEvents", "totalRevenue"):
            result.add_metric(
                name,
                row.get(name, 0),
                source="ga4_commerce_post_fix",
                dimensions={"event_name": row.get("eventName", ""), "host_name": row.get("hostName", "")},
            )

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

    if diagnostics["add_to_cart_missing"]:
        result.alerts.append(AlertSpec(
            dedupe_key="ga4:commerce-funnel-events-missing",
            severity="P1",
            category="ga4",
            title="GA4 no registra los productos añadidos al carrito",
            message=(
                f"La tienda registra {diagnostics['shop_sessions']:.0f} sesiones en 28 días, "
                f"pero add_to_cart={diagnostics['add_to_cart']:.0f}. "
                f"Purchase sí registra {diagnostics['purchases']:.0f} eventos, por lo que la venta funciona "
                "y el fallo está en la instrumentación del embudo."
            ),
            action="Validar el evento de WooCommerce al añadir un producto y corregir add_to_cart sin alterar el purchase que ya funciona.",
            evidence_url="https://analytics.google.com/",
            metadata=diagnostics,
        ))
    if diagnostics["begin_checkout_missing"]:
        result.alerts.append(AlertSpec(
            dedupe_key="ga4:begin-checkout-not-measured",
            severity="P2",
            category="ga4",
            title="GA4 no mide todavía el inicio del checkout",
            message=(
                f"La tienda registra {diagnostics['shop_sessions']:.0f} sesiones en 28 días y "
                f"{diagnostics['purchases']:.0f} compras, pero begin_checkout={diagnostics['begin_checkout']:.0f}."
            ),
            action="Añadir una medición begin_checkout sin duplicar add_to_cart ni purchase y validarla en DebugView.",
            evidence_url="https://analytics.google.com/",
            metadata=diagnostics,
        ))
    if historical_diagnostics["technical_sessions"] >= 10:
        result.alerts.append(AlertSpec(
            dedupe_key="ga4:technical-host-traffic",
            severity="P2",
            category="ga4",
            title="Tráfico técnico contamina la propiedad GA4",
            message=f"Se detectan {historical_diagnostics['technical_sessions']:.0f} sesiones de localhost/127.0.0.1 en 28 días.",
            action="Desactivar la etiqueta en desarrollo o aplicar un filtro de tráfico interno verificado, sin excluir tráfico real de web y tienda.",
            evidence_url="https://analytics.google.com/",
            metadata=historical_diagnostics,
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
        "commerce_period": [commerce_start.isoformat(), current_end.isoformat()],
        "funnel_evaluation_period": [funnel_start.isoformat(), current_end.isoformat()],
        "funnel_evaluation_ready": diagnostics["evaluation_ready"],
        "commerce_diagnostics": diagnostics,
        "commerce_baseline_diagnostics": historical_diagnostics,
        "commerce_events": commerce_rows,
        "funnel_events": funnel_rows,
        "channel_host_rows": channel_host_rows[:30],
        "alerts": len(result.alerts),
    }
    return result
