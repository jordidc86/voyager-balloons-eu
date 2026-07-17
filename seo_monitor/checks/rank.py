from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import requests

from ..config import Settings, load_keywords
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _search(settings: Settings, row: dict[str, str], depth: int) -> tuple[dict, float]:
    payload = {
        "keyword": row["keyword"],
        "location_name": row["location_name"],
        "language_code": row["language_code"],
        "device": row["device"],
        "depth": depth,
    }
    if row["device"] == "mobile":
        payload["os"] = "android"
    response = requests.post(
        ENDPOINT,
        auth=(settings.dataforseo_login or "", settings.dataforseo_password or ""),
        json=[payload],
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    task = data.get("tasks", [{}])[0]
    if task.get("status_code") != 20000:
        raise RuntimeError(task.get("status_message") or "DataForSEO no devolvió una tarea válida")
    result = task.get("result", [{}])[0]
    return (
        {"request": payload, "items": result.get("items", []), "check_url": result.get("check_url")},
        float(task.get("cost") or 0),
    )


def _is_due(previous, interval_days: int, now: datetime | None = None) -> bool:
    if previous is None:
        return True
    observed_at = previous.observed_at
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - observed_at >= timedelta(days=interval_days)


def _depth_for(row: dict[str, str], previous, thresholds: dict) -> int | None:
    if row.get("priority") == "P0":
        return int(thresholds.get("rank_critical_depth", 20))
    interval_days = int(thresholds.get("rank_secondary_interval_days", 7))
    if _is_due(previous, interval_days):
        return int(thresholds.get("rank_secondary_depth", 100))
    return None


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="rank")
    if not settings.dataforseo_login or not settings.dataforseo_password:
        result.status = "skipped"
        result.summary = {"reason": "DATAFORSEO_LOGIN/PASSWORD no configurados"}
        return result

    target_domains = {domain.removeprefix("www.") for domain in config["target_domains"]}
    thresholds = config["thresholds"]
    threshold = float(thresholds.get("rank_drop_positions", 3))
    keywords = load_keywords(settings)
    found = 0
    top_ten = 0
    failures = []
    total_cost = 0.0
    budget_limited = False
    checked = 0
    deferred = 0

    for row in keywords:
        previous = store.previous_keyword_ranking(row["keyword"], row["location_name"], row["device"])
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
            failures.append({"keyword": row["keyword"], "error": str(exc)})
            continue
        checked += 1

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

        key = f"rank:{row['language_code']}:{row['location_name']}:{row['device']}:{row['keyword']}"
        if previous and previous.position is not None and (position is not None or previous.position <= depth):
            if position is None or position - previous.position >= threshold:
                new_position = f">{depth}" if position is None else f"{position:.0f}"
                result.alerts.append(AlertSpec(
                    dedupe_key=f"{key}:drop",
                    severity="P1" if row["priority"] == "P0" else "P2",
                    category="rank",
                    title=f"Pérdida de posición: {row['keyword']}",
                    message=f"Voyager pasa de {previous.position:.0f} a {new_position} en {row['location_name']} ({row['device']}).",
                    action="Comprobar SERP, URL posicionada, competidor ascendente, indexación y cambios recientes antes de modificar contenido.",
                    evidence_url=row["target_url"], metadata={"previous": previous.position, "current": position, "top_domain": top_domain},
                ))
        elif position is None and row["priority"] == "P0":
            result.alerts.append(AlertSpec(
                dedupe_key=f"{key}:absent", severity="P2", category="rank",
                title=f"Sin visibilidad top {depth}: {row['keyword']}",
                message=f"No se encuentra Voyager entre los {depth} primeros resultados en {row['location_name']} ({row['device']}).",
                action="Auditar intención, indexación, autoridad y contenido de la landing objetivo; convertirlo en acción del backlog SEO.",
                evidence_url=row["target_url"], metadata={"top_domain": top_domain},
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
