from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote, urlsplit

from ..config import Settings, load_keywords
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


def _candidate_route(query: str, page: str) -> dict[str, str]:
    text = query.casefold()
    path = urlsplit(page).path.casefold()
    if "/pt/" in path or any(token in text for token in (" balão", " balao", "voo ", "passeio ")):
        language_code = "pt"
        location_name = "Portugal"
        location_code = "2620"
    elif "/en/" in path or any(token in text for token in ("balloon", "things to do", "day trip")):
        language_code = "en"
        location_name = "Madrid Spain"
        location_code = "1005493"
    else:
        language_code = "es"
        location_name = "Madrid Spain"
        location_code = "1005493"
    if "bragan" in text or "bragan" in path:
        cluster = "braganca"
        if language_code == "pt":
            location_name = "Braganca Portugal"
            location_code = "9051350"
        elif language_code == "en":
            location_name = "Portugal"
            location_code = "2620"
        else:
            location_name = "Spain"
            location_code = "2724"
    elif "regal" in text or "gift" in text or "regal" in path or "gift" in path:
        cluster = "gift"
    elif "comfort" in text or "comfort" in path or "pareja" in text or "couple" in text:
        cluster = "comfort"
    elif "madrid" in text or "madrid" in path or "day trip" in text:
        cluster = "madrid"
    else:
        cluster = "segovia"
    return {
        "language_code": language_code,
        "location_name": location_name,
        "location_code": location_code,
        "cluster": cluster,
    }


def _discover_keyword_candidates(
    rows: list[dict],
    existing_keywords: set[str],
    discovery_config: dict,
) -> list[dict]:
    minimum_impressions = float(discovery_config.get("minimum_impressions_28d", 20))
    commercial_terms = tuple(
        str(term).casefold() for term in discovery_config.get(
            "commercial_terms",
            ["globo", "balloon", "balão", "balao"],
        )
    )
    excluded_terms = tuple(
        str(term).casefold() for term in discovery_config.get("excluded_terms", ["voyager"])
    )
    grouped: dict[str, dict] = {}
    for row in rows:
        keys = row.get("keys", [])
        if len(keys) < 2:
            continue
        query = " ".join(str(keys[0]).casefold().split())
        page = str(keys[1])
        if not query or query in existing_keywords:
            continue
        if not any(term in query for term in commercial_terms) or any(term in query for term in excluded_terms):
            continue
        parsed = urlsplit(page)
        if parsed.netloc not in {"www.voyagerballoons.eu", "shop.voyagerballoons.eu"}:
            continue
        blocked_prefixes = (
            "/cart",
            "/carrito",
            "/checkout",
            "/finalizar-compra",
            "/my-account",
            "/mi-cuenta",
            "/wp-",
            "/tag/",
            "/feed/",
            "/categoria-producto/",
            "/etiqueta-producto/",
        )
        if parsed.query or parsed.path.casefold().startswith(blocked_prefixes):
            continue
        impressions = float(row.get("impressions", 0) or 0)
        clicks = float(row.get("clicks", 0) or 0)
        current = grouped.setdefault(query, {
            "query": query,
            "impressions": 0.0,
            "clicks": 0.0,
            "weighted_position": 0.0,
            "target_url": page,
            "best_page_score": (-1.0, -1.0),
        })
        current["impressions"] += impressions
        current["clicks"] += clicks
        current["weighted_position"] += float(row.get("position", 0) or 0) * impressions
        page_score = (clicks, impressions)
        if page_score > current["best_page_score"]:
            current["target_url"] = page
            current["best_page_score"] = page_score

    candidates = []
    for current in grouped.values():
        impressions = current["impressions"]
        if impressions < minimum_impressions:
            continue
        target_parts = urlsplit(current["target_url"])
        target_url = f"{target_parts.scheme}://{target_parts.netloc}{target_parts.path.rstrip('/') or '/'}"
        position = current["weighted_position"] / impressions if impressions else 0
        candidates.append({
            "query": current["query"],
            **_candidate_route(current["query"], target_url),
            "device": "mobile",
            "target_url": target_url,
            "priority": "P1",
            "source": "gsc",
            "impressions": impressions,
            "clicks": current["clicks"],
            "ctr": current["clicks"] / impressions if impressions else 0,
            "position": position,
        })
    candidates.sort(
        key=lambda item: (item["impressions"], item["clicks"], -item["position"]),
        reverse=True,
    )
    return candidates[:int(discovery_config.get("maximum_candidates_per_run", 20))]


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
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
    discovery_config = config.get("keyword_discovery", {})
    discovery_rows = []
    if discovery_config.get("enabled", True):
        discovery_start = current_end - timedelta(days=27)
        discovery_rows = _query(
            session,
            settings.gsc_property,
            discovery_start,
            current_end,
            ["query", "page"],
            row_limit=25000,
        )

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

    static_keywords = {
        " ".join(row["keyword"].casefold().split())
        for row in load_keywords(settings)
    }
    candidates = _discover_keyword_candidates(discovery_rows, static_keywords, discovery_config)
    active_candidates = store.active_keyword_candidates(
        limit=int(discovery_config.get("maximum_auto_active_keywords", 6))
    )
    active_queries = {candidate.query for candidate in active_candidates}
    available_slots = max(
        0,
        int(discovery_config.get("maximum_auto_active_keywords", 6)) - store.keyword_candidate_count("active"),
    )
    created_candidates = 0
    activated_candidates = []
    for candidate in candidates:
        if candidate["query"] in active_queries:
            candidate["status"] = "active"
        elif available_slots > 0:
            candidate["status"] = "active"
            available_slots -= 1
        else:
            candidate["status"] = "candidate"
        _, created, activated = store.upsert_keyword_candidate(run_id, candidate)
        created_candidates += int(created)
        if activated:
            activated_candidates.append(candidate)
    if activated_candidates:
        result.alerts.append(AlertSpec(
            dedupe_key="gsc:new-commercial-keywords",
            severity="P2",
            category="gsc",
            title="Nuevas consultas comerciales incorporadas al seguimiento",
            message=(
                f"Search Console ha activado {len(activated_candidates)} consultas reales nuevas "
                "sin superar el límite de inventario dinámico."
            ),
            action="Revisarlas en el informe semanal; solo crear o modificar contenido cuando la intención y la landing posicionada lo justifiquen.",
            evidence_url="https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:voyagerballoons.eu",
            metadata={"queries": activated_candidates},
        ))
    result.add_metric("keyword_candidates_discovered", len(candidates), source="gsc_discovery")
    result.add_metric("keyword_candidates_activated", len(activated_candidates), source="gsc_discovery")

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
        "keyword_candidates": len(candidates),
        "keyword_candidates_created": created_candidates,
        "keyword_candidates_activated": len(activated_candidates),
        "dynamic_keywords_active": store.keyword_candidate_count("active"),
        "alerts": len(result.alerts),
    }
    return result
