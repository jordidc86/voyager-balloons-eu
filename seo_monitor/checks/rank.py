from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
import time
from urllib.parse import urlsplit

import requests

from ..config import Settings, load_keyword_inventory
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"


class SearchError(RuntimeError):
    def __init__(self, message: str, cost: float = 0.0):
        super().__init__(message)
        self.cost = cost


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _normalized_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    host = parts.netloc.lower().removeprefix("www.")
    return f"{parts.scheme.lower()}://{host}{path}"


def _display_url(url: str | None) -> str | None:
    """Keep a readable URL while dropping provider tracking parameters and fragments."""
    if not url:
        return None
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}"


def _brand_target(config: dict, row: dict[str, str]) -> tuple[str, str, set[str]]:
    brand_id = row.get("brand_id") or "voyager"
    brand = config.get("brands", {}).get(brand_id, {})
    name = str(brand.get("name") or config.get("brand") or "Voyager Balloons")
    domains = brand.get("domains") or config["target_domains"]
    return brand_id, name, {str(domain).casefold().removeprefix("www.") for domain in domains}


def _accepted_alternate(config: dict, row: dict[str, str], ranking_url: str | None) -> bool:
    if not ranking_url:
        return False
    accepted = config.get("rank_accepted_alternates", {}).get(row["keyword"], [])
    normalized = _normalized_url(ranking_url)
    return normalized in {_normalized_url(url) for url in accepted}


def _drop_assessment(
    history: list,
    position: float | None,
    depth: int,
    threshold: float,
    minimum_history: int = 3,
) -> dict | None:
    if len(history) < minimum_history:
        return None
    values = [float(item.position) if item.position is not None else float(depth + 1) for item in history]
    baseline = float(median(values))
    current = float(position) if position is not None else float(depth + 1)
    if current - baseline < threshold:
        return None
    previous = values[0]
    return {
        "baseline": baseline,
        "current": current,
        "confirmed": previous - baseline >= threshold,
        "observations": len(values),
    }


def _drop_severity(
    priority: str,
    confirmed: bool,
    gsc_impressions: float,
    minimum_gsc_impressions: float,
    baseline: float,
    current: float,
) -> str:
    """Reserve urgent rank alerts for drops backed by real Search Console demand."""
    lost_high_visibility = (
        (baseline <= 10 < current)
        or (baseline <= 3 and current > 5)
    )
    if (
        priority == "P0"
        and confirmed
        and gsc_impressions >= minimum_gsc_impressions
        and lost_high_visibility
    ):
        return "P1"
    if gsc_impressions < minimum_gsc_impressions:
        return "P3"
    return "P2"


def _url_mismatch_severity(
    role: str | None,
    position: float | None,
    gsc_impressions: float,
    minimum_gsc_impressions: float,
) -> str:
    """Escalate only alternate URLs that combine demand with weak visibility."""
    if role == "cross_sell":
        return "P3"
    if position is None or position <= 10:
        return "P3"
    if gsc_impressions < minimum_gsc_impressions:
        return "P3"
    return "P2"


def _search(settings: Settings, row: dict[str, str], depth: int) -> tuple[dict, float]:
    payload = {
        "keyword": row["keyword"],
        "language_code": row["language_code"],
        "device": row["device"],
        "depth": depth,
    }
    if row.get("location_code"):
        payload["location_code"] = int(row["location_code"])
    else:
        payload["location_name"] = row["location_name"]
    if row["device"] == "mobile":
        payload["os"] = "android"
    total_cost = 0.0
    for attempt in range(3):
        try:
            response = requests.post(
                ENDPOINT,
                auth=(settings.dataforseo_login or "", settings.dataforseo_password or ""),
                json=[payload],
                timeout=90,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if attempt < 2 and (status_code is None or status_code >= 500):
                time.sleep(2 ** attempt)
                continue
            raise

        data = response.json()
        task = data.get("tasks", [{}])[0]
        total_cost += float(task.get("cost") or 0)
        if task.get("status_code") == 20000:
            result = task.get("result", [{}])[0]
            return (
                {"request": payload, "items": result.get("items", []), "check_url": result.get("check_url")},
                total_cost,
            )

        message = task.get("status_message") or "DataForSEO no devolvió una tarea válida"
        if attempt < 2 and (int(task.get("status_code") or 0) >= 50000 or "internal" in message.lower()):
            time.sleep(2 ** attempt)
            continue
        raise SearchError(message, total_cost)

    raise SearchError("DataForSEO agotó los reintentos", total_cost)


def _is_due(previous, interval_days: int, now: datetime | None = None) -> bool:
    if previous is None:
        return True
    observed_at = previous.observed_at
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - observed_at >= timedelta(days=interval_days)


def _depth_for(
    row: dict[str, str],
    previous,
    thresholds: dict,
    now: datetime | None = None,
) -> int | None:
    if row.get("priority") == "P0":
        return int(thresholds.get("rank_critical_depth", 20))
    interval_days = int(thresholds.get("rank_secondary_interval_days", 7))
    if _is_due(previous, interval_days, now=now):
        return int(thresholds.get("rank_secondary_depth", 100))
    return None


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="rank")
    if not settings.dataforseo_login or not settings.dataforseo_password:
        result.status = "skipped"
        result.summary = {"reason": "DATAFORSEO_LOGIN/PASSWORD no configurados"}
        return result

    thresholds = config["thresholds"]
    threshold = float(thresholds.get("rank_drop_positions", 3))
    keywords = load_keyword_inventory(
        settings,
        store,
        dynamic_limit=int(config.get("keyword_discovery", {}).get("maximum_auto_active_keywords", 6)),
    )
    found = 0
    top_ten = 0
    failures = []
    total_cost = 0.0
    budget_limited = False
    checked = 0
    deferred = 0
    result.resolution_prefixes = ["rank:provider-failures"]

    for row in keywords:
        history = store.keyword_ranking_history(
            row["keyword"],
            row["location_name"],
            row["device"],
            limit=int(thresholds.get("rank_drop_history_window", 7)),
            target_url=row["target_url"],
        )
        previous = history[0] if history else None
        depth = _depth_for(row, previous, thresholds)
        if depth is None:
            deferred += 1
            continue
        if not budget_available(config, total_cost):
            budget_limited = True
            break
        try:
            serp, cost = _search(settings, row, depth)
            total_cost += cost
        except Exception as exc:
            total_cost += float(getattr(exc, "cost", 0) or 0)
            failures.append({"keyword": row["keyword"], "error": str(exc)})
            continue
        checked += 1

        brand_id, brand_name, target_domains = _brand_target(config, row)

        organic = [item for item in serp["items"] if item.get("type") == "organic"]
        matching = next((item for item in organic if _domain(item.get("url")) in target_domains), None)
        position = float(matching.get("rank_absolute")) if matching else None
        ranking_url = matching.get("url") if matching else None
        top_domain = _domain(organic[0].get("url")) if organic else None
        payload = {
            **row,
            "position": position,
            "ranking_url": ranking_url,
            "top_domain": top_domain,
            "check_url": serp.get("check_url"),
            "depth": depth,
            "top_results": [
                {"position": item.get("rank_absolute"), "domain": _domain(item.get("url")), "url": item.get("url")}
                for item in organic[:10]
            ],
        }
        store.add_keyword_ranking(run_id, payload)
        found += int(position is not None)
        top_ten += int(position is not None and position <= 10)
        result.add_metric(
            "position", position or 101, source="rank",
            dimensions={"keyword": row["keyword"], "location": row["location_name"], "device": row["device"], "cluster": row["cluster"]},
        )

        legacy_key = f"rank:{row['language_code']}:{row['location_name']}:{row['device']}:{row['keyword']}"
        key = f"rank:{brand_id}:{row['language_code']}:{row['location_name']}:{row['device']}:{row['keyword']}"
        result.resolution_prefixes.extend([legacy_key, key])
        drop = _drop_assessment(
            history,
            position,
            depth,
            threshold,
            minimum_history=int(thresholds.get("rank_drop_minimum_history", 3)),
        )
        if drop:
            new_position = f">{depth}" if position is None else f"{position:.0f}"
            gsc_impressions = store.latest_gsc_query_impressions(row["keyword"])
            minimum_gsc_impressions = float(
                thresholds.get("rank_p1_minimum_gsc_impressions", 10)
            )
            severity = _drop_severity(
                row["priority"],
                drop["confirmed"],
                gsc_impressions,
                minimum_gsc_impressions,
                drop["baseline"],
                drop["current"],
            )
            action = (
                "Confirmar la tendencia, URL posicionada, competidor ascendente, indexación y cambios recientes antes de modificar contenido."
            )
            if gsc_impressions < minimum_gsc_impressions:
                action += (
                    " Search Console no confirma demanda suficiente para tratarlo como urgente; mantener en observación y trabajar la consolidación semántica."
                )
            result.alerts.append(AlertSpec(
                dedupe_key=f"{key}:drop",
                severity=severity,
                category="rank",
                title=f"Pérdida de posición: {row['keyword']}",
                message=(
                    f"{brand_name} está en {new_position}, frente a una referencia estable de "
                    f"{drop['baseline']:.0f}, en {row['location_name']} ({row['device']})."
                ),
                action=action,
                evidence_url=row["target_url"],
                metadata={
                    **drop,
                    "position": position,
                    "ranking_url": ranking_url,
                    "target_url": row["target_url"],
                    "top_domain": top_domain,
                    "gsc_query_impressions_7d": gsc_impressions,
                    "rank_p1_minimum_gsc_impressions": minimum_gsc_impressions,
                },
            ))
        elif position is None and row["priority"] == "P0":
            gsc_impressions = store.latest_gsc_query_impressions(row["keyword"])
            minimum_gsc_impressions = float(
                thresholds.get("rank_p1_minimum_gsc_impressions", 10)
            )
            result.alerts.append(AlertSpec(
                dedupe_key=f"{key}:absent",
                severity="P2" if gsc_impressions >= minimum_gsc_impressions else "P3",
                category="rank",
                title=f"Sin visibilidad top {depth}: {row['keyword']}",
                message=f"No se encuentra {brand_name} entre los {depth} primeros resultados en {row['location_name']} ({row['device']}).",
                action="Auditar intención, indexación, autoridad y contenido de la landing objetivo; convertirlo en acción del backlog SEO.",
                evidence_url=row["target_url"],
                metadata={
                    "brand_id": brand_id,
                    "brand_name": brand_name,
                    "top_domain": top_domain,
                    "gsc_query_impressions_7d": gsc_impressions,
                },
            ))

        accepted_alternate = _accepted_alternate(config, row, ranking_url)
        result.add_metric(
            "accepted_alternate_url",
            int(accepted_alternate),
            source="rank",
            dimensions={"keyword": row["keyword"], "brand_id": brand_id},
        )
        if (
            ranking_url
            and not drop
            and not accepted_alternate
            and _normalized_url(ranking_url) != _normalized_url(row["target_url"])
        ):
            displayed_ranking_url = _display_url(ranking_url)
            displayed_target_url = _display_url(row["target_url"])
            gsc_impressions = store.latest_gsc_query_impressions(row["keyword"])
            minimum_gsc_impressions = float(
                thresholds.get("rank_p1_minimum_gsc_impressions", 10)
            )
            result.alerts.append(AlertSpec(
                dedupe_key=f"{key}:url-mismatch",
                severity=_url_mismatch_severity(
                    row.get("role"),
                    position,
                    gsc_impressions,
                    minimum_gsc_impressions,
                ),
                category="rank",
                title=f"Google elige otra landing: {row['keyword']}",
                message=(
                    f"Google muestra {displayed_ranking_url} para {brand_name} en lugar de la landing objetivo "
                    f"{displayed_target_url}. Los parámetros de seguimiento se han ignorado en la comparación."
                ),
                action=(
                    "Revisar intención, títulos, enlaces internos y relevancia de ambas páginas. "
                    "Tratar la home frente a una landing como desajuste de destino, no como duplicación por parámetros; "
                    "no redirigir ni cambiar canonical sin validar la intención."
                ),
                evidence_url=row["target_url"],
                metadata={
                    "brand_id": brand_id,
                    "brand_name": brand_name,
                    "role": row.get("role") or "primary",
                    "ranking_url": displayed_ranking_url,
                    "provider_ranking_url": ranking_url,
                    "target_url": displayed_target_url,
                    "position": position,
                    "gsc_query_impressions_7d": gsc_impressions,
                },
            ))

    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="rank:provider-failures", severity="P1", category="rank",
            title="Fallos parciales en el seguimiento de posiciones",
            message=f"No se pudieron consultar {len(failures)} de {len(keywords)} palabras clave.",
            action="Revisar saldo, credenciales, ubicaciones admitidas y respuesta de DataForSEO antes de reintentar.",
            metadata={"failures": failures[:20]},
        ))
    result.summary = {
        "keywords_inventory": len(keywords),
        "keywords_checked": checked,
        "keywords_deferred": deferred,
        "found_in_requested_depth": found,
        "found_top_10": top_ten,
        "failures": len(failures),
        "provider_cost_usd": round(total_cost, 4),
        "run_budget_usd": dataforseo_run_budget(config),
        "budget_limited": budget_limited,
        "alerts": len(result.alerts),
    }
    result.add_metric("keywords_tracked", checked)
    result.add_metric("keywords_found_in_requested_depth", found)
    result.add_metric("keywords_top_10", top_ten)
    result.add_metric("provider_cost_usd", total_cost, source="rank")
    return result
