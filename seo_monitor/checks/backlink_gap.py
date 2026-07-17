from __future__ import annotations

import requests

from ..config import Settings
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/backlinks/referring_domains/live"


def _referring_domains(settings: Settings, target: str) -> tuple[list[dict], float]:
    payload = {
        "target": target.removeprefix("www."),
        "include_subdomains": True,
        "exclude_internal_backlinks": True,
        "backlinks_status_type": "live",
        "backlinks_filters": ["dofollow", "=", True],
        "rank_scale": "one_hundred",
        "limit": 100,
        "order_by": ["rank,desc"],
    }
    response = requests.post(
        ENDPOINT,
        auth=(settings.dataforseo_login or "", settings.dataforseo_password or ""),
        json=[payload],
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    task = data.get("tasks", [{}])[0]
    if task.get("status_code") != 20000:
        raise RuntimeError(task.get("status_message") or "DataForSEO Backlinks no devolvió una tarea válida")
    api_result = task.get("result", [{}])[0]
    return api_result.get("items", []), float(task.get("cost") or 0)


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="backlink_gap")
    if not settings.dataforseo_login or not settings.dataforseo_password:
        result.status = "skipped"
        result.summary = {"reason": "DATAFORSEO_LOGIN/PASSWORD no configurados"}
        return result

    competitors = config.get("backlink_gap_competitors", [])
    primary_domain = config["primary_domain"].removeprefix("www.")
    targets = [{"name": "Voyager Balloons", "domain": primary_domain}, *competitors]
    opportunities: dict[str, dict] = {}
    referring_domains: dict[str, dict[str, dict]] = {}
    failures = []
    total_cost = 0.0
    budget_limited = False
    thresholds = config.get("thresholds", {})
    minimum_rank = float(thresholds.get("backlink_gap_minimum_rank", 8))
    maximum_spam = float(thresholds.get("backlink_gap_maximum_spam_score", 30))

    for target in targets:
        if not budget_available(config, total_cost):
            budget_limited = True
            break
        try:
            items, cost = _referring_domains(settings, target["domain"])
            total_cost += cost
        except Exception as exc:
            failures.append({"target": target["name"], "error": str(exc)})
            continue
        referring_domains[target["name"]] = {
            str(item.get("domain") or "").lower().removeprefix("www.").strip("/"): item
            for item in items
            if item.get("domain")
        }

    voyager_domains = set(referring_domains.get("Voyager Balloons", {}))
    excluded_domains = {primary_domain, *(item["domain"].removeprefix("www.") for item in competitors)}
    for competitor in competitors:
        for referring_domain, item in referring_domains.get(competitor["name"], {}).items():
            if referring_domain in voyager_domains or referring_domain in excluded_domains:
                continue
            rank = float(item.get("rank") or 0)
            spam_score = float(item.get("backlinks_spam_score") or 0)
            if rank < minimum_rank or spam_score > maximum_spam:
                continue
            platforms = item.get("referring_links_platform_types") or {}
            editorial_bonus = 4 if any(platforms.get(key) for key in ("news", "blogs", "organization")) else 0
            opportunity = opportunities.setdefault(referring_domain, {
                "domain": referring_domain,
                "rank": rank,
                "spam_score": spam_score,
                "competitors": set(),
                "backlinks": 0,
                "countries": {},
                "editorial_bonus": editorial_bonus,
            })
            opportunity["rank"] = max(opportunity["rank"], rank)
            opportunity["spam_score"] = max(opportunity["spam_score"], spam_score)
            opportunity["competitors"].add(competitor["name"])
            opportunity["backlinks"] += int(item.get("backlinks") or 0)
            opportunity["editorial_bonus"] = max(opportunity["editorial_bonus"], editorial_bonus)
            for country, count in (item.get("referring_links_countries") or {}).items():
                opportunity["countries"][country] = opportunity["countries"].get(country, 0) + int(count or 0)

    ranked = []
    for opportunity in opportunities.values():
        opportunity["competitors"] = sorted(opportunity["competitors"])
        opportunity["score"] = round(
            min(
                100,
                opportunity["rank"]
                + len(opportunity["competitors"]) * 8
                + opportunity["editorial_bonus"]
                - opportunity["spam_score"],
            ),
            1,
        )
        ranked.append(opportunity)
    ranked.sort(key=lambda item: (item["score"], item["rank"], len(item["competitors"])), reverse=True)

    for opportunity in ranked[:100]:
        store.add_page_snapshot(run_id, "backlink_gap", {
            "url": f"https://{opportunity['domain']}",
            "status_code": None,
            "title": opportunity["domain"],
            "content_hash": None,
            **opportunity,
        })

    if ranked:
        result.alerts.append(AlertSpec(
            dedupe_key="backlink_gap:qualified-opportunities",
            severity="P2",
            category="backlink_gap",
            title="Nuevas oportunidades de enlaces frente a competidores",
            message=f"Se han identificado {len(ranked)} dominios relevantes que enlazan a competidores directos y no a Voyager.",
            action="Revisar los dominios mejor puntuados, descartar medios irrelevantes y preparar colaboraciones editoriales personalizadas por tandas aprobadas.",
            metadata={"opportunities": ranked[:30]},
        ))
    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="backlink_gap:provider-failures",
            severity="P1",
            category="backlink_gap",
            title="Comparación de backlinks incompleta",
            message=f"Fallaron {len(failures)} de {len(targets)} dominios previstos.",
            action="Revisar credenciales, saldo y respuesta del proveedor antes de usar la lista de oportunidades.",
            metadata={"failures": failures},
        ))

    result.summary = {
        "competitors": len(competitors),
        "targets_checked": len(referring_domains),
        "qualified_opportunities": len(ranked),
        "failures": len(failures),
        "provider_cost_usd": round(total_cost, 4),
        "run_budget_usd": dataforseo_run_budget(config),
        "budget_limited": budget_limited,
        "alerts": len(result.alerts),
    }
    result.add_metric("qualified_opportunities", len(ranked), source="backlink_gap")
    result.add_metric("provider_cost_usd", total_cost, source="backlink_gap")
    return result
