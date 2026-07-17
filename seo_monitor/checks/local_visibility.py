from __future__ import annotations

from statistics import median

import requests

from ..config import Settings
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/serp/google/maps/live/advanced"


def _absence_streak(history: list, current_position: float | None) -> int:
    if current_position is not None:
        return 0
    streak = 1
    for item in history:
        if item.position is not None:
            break
        streak += 1
    return streak


def _drop_assessment(history: list, current_position: float | None, threshold: float) -> dict | None:
    if current_position is None:
        return None
    positions = [float(item.position) for item in history if item.position is not None]
    if len(positions) < 3:
        return None
    baseline = float(median(positions))
    if float(current_position) - baseline < threshold:
        return None
    return {
        "baseline": baseline,
        "current": float(current_position),
        "confirmed": positions[0] - baseline >= threshold,
    }


def _rating(item: dict) -> tuple[float | None, int | None]:
    rating = item.get("rating")
    if isinstance(rating, dict):
        return rating.get("value"), rating.get("votes_count")
    if isinstance(rating, (int, float)):
        return float(rating), item.get("reviews_count")
    return None, item.get("reviews_count")


def _search(settings: Settings, check: dict) -> tuple[dict, float]:
    payload = {
        "keyword": check["keyword"],
        "language_code": check["language_code"],
        "location_coordinate": check["location_coordinate"],
        "device": "mobile",
        "os": "android",
        "depth": 20,
        "search_this_area": True,
        "search_places": False,
    }
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
        raise RuntimeError(task.get("status_message") or "DataForSEO Maps no devolvió una tarea válida")
    api_result = task.get("result", [{}])[0]
    return api_result, float(task.get("cost") or 0)


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="local_visibility")
    if not settings.dataforseo_login or not settings.dataforseo_password:
        result.status = "skipped"
        result.summary = {"reason": "DATAFORSEO_LOGIN/PASSWORD no configurados"}
        return result

    local_config = config.get("local_visibility", {})
    target_cid = str(local_config.get("cid") or "")
    target_name = str(local_config.get("business_name") or "").casefold()
    checks = local_config.get("checks", [])
    found = 0
    top_three = 0
    failures = []
    total_cost = 0.0
    budget_limited = False

    for check in checks:
        if not budget_available(config, total_cost):
            budget_limited = True
            break
        history = store.local_ranking_history(
            check["keyword"],
            check["location_label"],
            limit=int(config["thresholds"].get("local_visibility_history_window", 7)),
        )
        previous = history[0] if history else None
        try:
            api_result, cost = _search(settings, check)
            total_cost += cost
        except Exception as exc:
            failures.append({"keyword": check["keyword"], "location": check["location_label"], "error": str(exc)})
            continue

        items = [item for item in api_result.get("items", []) if item.get("type") == "maps_search"]
        matching = next(
            (
                item for item in items
                if (target_cid and str(item.get("cid") or "") == target_cid)
                or (target_name and target_name in str(item.get("title") or "").casefold())
            ),
            None,
        )
        position = float(matching.get("rank_absolute")) if matching else None
        rating, reviews_count = _rating(matching or {})
        payload = {
            "keyword": check["keyword"],
            "language_code": check["language_code"],
            "location_label": check["location_label"],
            "location_coordinate": check["location_coordinate"],
            "position": position,
            "title": matching.get("title") if matching else None,
            "cid": str(matching.get("cid")) if matching and matching.get("cid") else None,
            "place_id": matching.get("place_id") if matching else None,
            "rating": rating,
            "reviews_count": reviews_count,
            "check_url": api_result.get("check_url"),
            "top_results": [
                {
                    "position": item.get("rank_absolute"),
                    "title": item.get("title"),
                    "cid": item.get("cid"),
                    "rating": item.get("rating"),
                }
                for item in items[:10]
            ],
        }
        store.add_local_ranking(run_id, payload)
        found += int(position is not None)
        top_three += int(position is not None and position <= 3)
        result.add_metric(
            "maps_position",
            position or 21,
            source="local_visibility",
            dimensions={"keyword": check["keyword"], "location": check["location_label"]},
        )

        key = f"local_visibility:{check['location_label']}:{check['keyword']}"
        drop = _drop_assessment(
            history,
            position,
            float(config["thresholds"].get("rank_drop_positions", 3)),
        )
        if drop:
            severity = "P1" if check.get("priority") == "P0" and drop["confirmed"] else "P2"
            result.alerts.append(AlertSpec(
                dedupe_key=f"{key}:drop",
                severity=severity,
                category="local_visibility",
                title=f"Caída en Google Maps: {check['keyword']}",
                message=(
                    f"La ficha está en la posición {position:.0f}, frente a una referencia estable "
                    f"de {drop['baseline']:.0f}, en {check['location_label']}."
                ),
                action="Confirmar la tendencia y revisar reseñas, categoría, servicios y competidores del mapa antes de editar la ficha.",
                evidence_url=api_result.get("check_url"),
                metadata={**drop, "top_results": payload["top_results"]},
            ))
        absence_streak = _absence_streak(history, position)
        if (
            check.get("required")
            and absence_streak >= int(config["thresholds"].get("local_visibility_absence_confirmations", 3))
        ):
            result.alerts.append(AlertSpec(
                dedupe_key=f"{key}:absent",
                severity="P2",
                category="local_visibility",
                title=f"Sin visibilidad top 20 en Google Maps: {check['keyword']}",
                message=(
                    f"La ficha no aparece entre los 20 resultados móviles durante "
                    f"{absence_streak} mediciones consecutivas en {check['location_label']}. "
                    "Esto no significa que el perfil haya desaparecido."
                ),
                action="Comparar las fichas visibles, comprobar elegibilidad del área de servicio y preparar mejoras verificables de categoría, servicios, fotos y reseñas.",
                evidence_url=api_result.get("check_url"),
                metadata={"absence_streak": absence_streak, "top_results": payload["top_results"]},
            ))

    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="local_visibility:provider-failures",
            severity="P1",
            category="local_visibility",
            title="Fallos parciales al medir Google Maps",
            message=f"No se pudieron consultar {len(failures)} de {len(checks)} combinaciones locales.",
            action="Revisar credenciales, saldo y parámetros geográficos de DataForSEO.",
            metadata={"failures": failures[:20]},
        ))

    result.summary = {
        "checks": len(checks),
        "found_top_20": found,
        "found_top_3": top_three,
        "failures": len(failures),
        "provider_cost_usd": round(total_cost, 4),
        "run_budget_usd": dataforseo_run_budget(config),
        "budget_limited": budget_limited,
        "alerts": len(result.alerts),
    }
    result.add_metric("checks", len(checks), source="local_visibility")
    result.add_metric("found_top_20", found, source="local_visibility")
    result.add_metric("found_top_3", top_three, source="local_visibility")
    result.add_metric("provider_cost_usd", total_cost, source="local_visibility")
    return result
