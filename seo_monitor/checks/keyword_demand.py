from __future__ import annotations

from collections import defaultdict

import requests

from ..config import Settings, load_keyword_inventory
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live"


def _market(row: dict[str, str]) -> tuple[str, str, int]:
    is_portugal = "braganca" in row.get("cluster", "")
    language_code = row.get("language_code") or ("pt" if is_portugal else "es")
    if is_portugal:
        return "Portugal", language_code, 2620
    return "Spain", language_code, 2724


def _overview(
    settings: Settings,
    keywords: list[str],
    api_language_code: str,
    location_code: int,
    tag: str,
) -> tuple[list[dict], float]:
    response = requests.post(
        ENDPOINT,
        auth=(settings.dataforseo_login or "", settings.dataforseo_password or ""),
        json=[{
            "language_code": api_language_code,
            "location_code": location_code,
            "keywords": keywords,
            "include_serp_info": True,
            "tag": tag,
        }],
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    task = data.get("tasks", [{}])[0]
    if task.get("status_code") != 20000:
        raise RuntimeError(task.get("status_message") or "DataForSEO Labs no devolvió una tarea válida")
    api_result = (task.get("result") or [{}])[0] or {}
    return api_result.get("items") or [], float(task.get("cost") or 0)


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="keyword_demand")
    if not settings.dataforseo_login or not settings.dataforseo_password:
        result.status = "skipped"
        result.summary = {"reason": "DATAFORSEO_LOGIN/PASSWORD no configurados"}
        return result

    inventory = load_keyword_inventory(
        settings,
        store,
        dynamic_limit=int(config.get("keyword_discovery", {}).get("maximum_auto_active_keywords", 6)),
    )
    grouped: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in inventory:
        market_name, api_language_code, location_code = _market(row)
        grouped[(market_name, api_language_code, location_code)].append(row)

    total_cost = 0.0
    data_by_keyword: dict[tuple[str, int, str], dict] = {}
    failures = []
    budget_limited = False
    groups_checked = 0
    for (market_name, api_language_code, location_code), rows in grouped.items():
        if not budget_available(config, total_cost):
            budget_limited = True
            break
        try:
            items, cost = _overview(
                settings,
                [row["keyword"] for row in rows],
                api_language_code,
                location_code,
                f"{market_name.lower()}:{api_language_code}",
            )
            total_cost += cost
            groups_checked += 1
        except Exception as exc:
            failures.append({"market": market_name, "error": str(exc)})
            continue
        for item in items:
            data_by_keyword[(market_name, location_code, str(item.get("keyword") or "").lower())] = item

    opportunities = []
    keywords_with_data = 0
    for row in inventory:
        market_name, _, location_code = _market(row)
        item = data_by_keyword.get((market_name, location_code, row["keyword"].lower()))
        if not item:
            continue
        keywords_with_data += 1
        keyword_info = item.get("keyword_info") or {}
        intent_info = item.get("search_intent_info") or {}
        properties = item.get("keyword_properties") or {}
        volume = int(keyword_info.get("search_volume") or 0)
        cpc = float(keyword_info.get("cpc") or 0)
        difficulty = properties.get("keyword_difficulty")
        previous = store.previous_keyword_ranking(row["keyword"], row["location_name"], row["device"])
        position = previous.position if previous else None
        payload = {
            **row,
            "market": market_name,
            "search_volume": volume,
            "cpc": cpc,
            "competition": keyword_info.get("competition"),
            "competition_level": keyword_info.get("competition_level"),
            "intent": intent_info.get("main_intent"),
            "keyword_difficulty": difficulty,
            "current_position": position,
            "url": row["target_url"],
            "title": row["keyword"],
            "status_code": None,
            "content_hash": None,
        }
        store.add_page_snapshot(run_id, "keyword_demand", payload)
        result.add_metric(
            "monthly_search_volume",
            volume,
            source="keyword_demand",
            dimensions={"keyword": row["keyword"], "market": market_name, "cluster": row["cluster"]},
        )
        result.add_metric(
            "cpc_usd",
            cpc,
            source="keyword_demand",
            dimensions={"keyword": row["keyword"], "market": market_name, "cluster": row["cluster"]},
        )
        if volume >= 50 and (position is None or position > 10):
            opportunities.append({
                "keyword": row["keyword"],
                "search_volume": volume,
                "cpc": cpc,
                "intent": intent_info.get("main_intent"),
                "difficulty": difficulty,
                "position": position,
                "target_url": row["target_url"],
                "priority": row["priority"],
            })

    opportunities.sort(
        key=lambda item: (item["priority"] == "P0", item["cpc"], item["search_volume"]),
        reverse=True,
    )
    if opportunities:
        result.alerts.append(AlertSpec(
            dedupe_key="keyword_demand:high-opportunities",
            severity="P2",
            category="keyword_demand",
            title="Palabras clave con demanda fuera del top 10",
            message=f"Hay {len(opportunities)} consultas con demanda relevante en las que Voyager aún no está consolidado en top 10.",
            action="Priorizar las páginas por intención comercial, CPC y volumen; comprobar primero canibalización, URL posicionada y enlaces internos.",
            metadata={"opportunities": opportunities[:20]},
        ))
    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="keyword_demand:provider-failures",
            severity="P1",
            category="keyword_demand",
            title="Datos de demanda incompletos",
            message=f"No se pudieron consultar {len(failures)} mercados.",
            action="Revisar saldo, idiomas admitidos y respuesta de DataForSEO Labs antes del siguiente ciclo.",
            metadata={"failures": failures},
        ))

    result.summary = {
        "keywords_inventory": len(inventory),
        "keywords_with_data": keywords_with_data,
        "groups_checked": groups_checked,
        "opportunities": len(opportunities),
        "failures": len(failures),
        "provider_cost_usd": round(total_cost, 4),
        "run_budget_usd": dataforseo_run_budget(config),
        "budget_limited": budget_limited,
        "alerts": len(result.alerts),
    }
    result.add_metric("keywords_with_demand_data", keywords_with_data, source="keyword_demand")
    result.add_metric("provider_cost_usd", total_cost, source="keyword_demand")
    return result
