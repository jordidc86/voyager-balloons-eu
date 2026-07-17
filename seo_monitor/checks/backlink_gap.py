from __future__ import annotations

from itertools import combinations

import requests

from ..config import Settings
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/backlinks/domain_intersection/live"


def _intersection(settings: Settings, left: dict, right: dict, primary_domain: str) -> tuple[list[dict], float]:
    payload = {
        "targets": {"1": left["domain"], "2": right["domain"]},
        "exclude_targets": [primary_domain.removeprefix("www.")],
        "include_subdomains": True,
        "exclude_internal_backlinks": True,
        "backlinks_status_type": "live",
        "backlinks_filters": [["dofollow", "=", True]],
        "rank_scale": "one_hundred",
        "limit": 100,
        "order_by": ["1.rank,desc"],
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
    pairs = list(combinations(competitors, 2))
    opportunities: dict[str, dict] = {}
    failures = []
    total_cost = 0.0
    budget_limited = False

    for left, right in pairs:
        if not budget_available(config, total_cost):
            budget_limited = True
            break
        try:
            items, cost = _intersection(settings, left, right, config["primary_domain"])
            total_cost += cost
        except Exception as exc:
            failures.append({"competitors": [left["name"], right["name"]], "error": str(exc)})
            continue

        for item in items:
            intersection = item.get("domain_intersection", {})
            details = [value for value in intersection.values() if isinstance(value, dict)]
            referring_domain = next((str(value.get("target") or "") for value in details if value.get("target")), "")
            referring_domain = referring_domain.removeprefix("www.").strip("/")
            if not referring_domain:
                continue
            rank = max((float(value.get("rank") or 0) for value in details), default=0)
            spam_score = max((float(value.get("backlinks_spam_score") or 0) for value in details), default=0)
            if rank < 15 or spam_score > 30:
                continue
            opportunity = opportunities.setdefault(referring_domain, {
                "domain": referring_domain,
                "rank": rank,
                "spam_score": spam_score,
                "competitors": set(),
                "pair_count": 0,
            })
            opportunity["rank"] = max(opportunity["rank"], rank)
            opportunity["spam_score"] = max(opportunity["spam_score"], spam_score)
            opportunity["competitors"].update({left["name"], right["name"]})
            opportunity["pair_count"] += 1

    ranked = []
    for opportunity in opportunities.values():
        opportunity["competitors"] = sorted(opportunity["competitors"])
        opportunity["score"] = round(
            min(100, opportunity["rank"] + opportunity["pair_count"] * 8 - opportunity["spam_score"]),
            1,
        )
        ranked.append(opportunity)
    ranked.sort(key=lambda item: (item["score"], item["rank"], item["pair_count"]), reverse=True)

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
            message=f"Se han identificado {len(ranked)} dominios que enlazan a varios competidores directos y no a Voyager.",
            action="Revisar los dominios mejor puntuados, descartar medios irrelevantes y preparar colaboraciones editoriales personalizadas por tandas aprobadas.",
            metadata={"opportunities": ranked[:30]},
        ))
    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="backlink_gap:provider-failures",
            severity="P1",
            category="backlink_gap",
            title="Cruce de backlinks incompleto",
            message=f"Fallaron {len(failures)} de {len(pairs)} cruces previstos.",
            action="Revisar credenciales, saldo y respuesta del proveedor antes de usar la lista de oportunidades.",
            metadata={"failures": failures},
        ))

    result.summary = {
        "competitors": len(competitors),
        "pair_checks": len(pairs),
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
