from __future__ import annotations

import json

import requests

from ..config import Settings
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINT = "https://api.dataforseo.com/v3/backlinks/referring_domains/live"


def _domain(value: str) -> str:
    return value.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")


def _referring_domains(
    settings: Settings,
    target: str,
    *,
    limit: int = 100,
    dofollow_only: bool = True,
) -> tuple[list[dict], float]:
    payload = {
        "target": _domain(target),
        "include_subdomains": True,
        "exclude_internal_backlinks": True,
        "backlinks_status_type": "live",
        "rank_scale": "one_hundred",
        "limit": max(1, min(1000, int(limit))),
        "order_by": ["rank,desc"],
    }
    if dofollow_only:
        payload["backlinks_filters"] = ["dofollow", "=", True]
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
    task_results = task.get("result") or [{}]
    api_result = task_results[0]
    return api_result.get("items") or [], float(task.get("cost") or 0)


def _profile_record(item: dict) -> dict:
    domain = _domain(str(item.get("domain") or ""))
    referring_pages = int(item.get("referring_pages") or 0)
    nofollow_pages = int(item.get("referring_pages_nofollow") or 0)
    return {
        "url": f"https://{domain}",
        "domain": domain,
        "present": True,
        "miss_streak": 0,
        "rank": float(item.get("rank") or 0),
        "spam_score": float(item.get("backlinks_spam_score") or 0),
        "backlinks": int(item.get("backlinks") or 0),
        "referring_pages": referring_pages,
        "nofollow_pages": nofollow_pages,
        "dofollow_pages": max(0, referring_pages - nofollow_pages),
        "first_seen": item.get("first_seen"),
        "platforms": item.get("referring_links_platform_types") or {},
        "countries": item.get("referring_links_countries") or {},
    }


def _missing_record(previous: dict) -> dict:
    return {
        **previous,
        "url": previous["url"],
        "domain": previous["domain"],
        "present": False,
        "miss_streak": int(previous.get("miss_streak") or 0) + 1,
    }


def _quality(record: dict, minimum_rank: float, maximum_spam: float) -> bool:
    return (
        float(record.get("rank") or 0) >= minimum_rank
        and float(record.get("spam_score") or 0) <= maximum_spam
        and int(record.get("dofollow_pages") or 0) > 0
    )


def _update_profile(
    store: Store,
    run_id: int,
    items: list[dict],
    minimum_rank: float,
    maximum_spam: float,
    loss_confirmations: int,
) -> dict:
    previous_snapshots = store.page_snapshots_for_latest_success("backlink_profile", "backlink_gap")
    previous = {}
    for snapshot in previous_snapshots:
        payload = json.loads(snapshot.payload_json)
        domain = _domain(str(payload.get("domain") or ""))
        if domain:
            previous[domain] = payload
    current = {
        record["domain"]: record
        for record in (_profile_record(item) for item in items if item.get("domain"))
    }
    baseline_initialized = bool(previous_snapshots)
    new_domains = []
    recovered_domains = []
    missing_once = []
    confirmed_lost = []

    records = dict(current)
    for domain, record in current.items():
        old = previous.get(domain)
        if not baseline_initialized:
            continue
        if old is None:
            if _quality(record, minimum_rank, maximum_spam):
                new_domains.append(record)
        elif not old.get("present", True):
            recovered_domains.append(record)

    for domain, old in previous.items():
        if domain in current:
            continue
        missing = _missing_record(old)
        records[domain] = missing
        if not _quality(missing, minimum_rank, maximum_spam):
            continue
        if missing["miss_streak"] >= loss_confirmations:
            confirmed_lost.append(missing)
        else:
            missing_once.append(missing)

    for record in records.values():
        store.add_page_snapshot(run_id, "backlink_profile", record)

    return {
        "baseline_initialized": baseline_initialized,
        "domains": len(current),
        "dofollow_domains": sum(1 for item in current.values() if item["dofollow_pages"] > 0),
        "new_domains": sorted(new_domains, key=lambda item: item["rank"], reverse=True),
        "recovered_domains": sorted(recovered_domains, key=lambda item: item["rank"], reverse=True),
        "missing_once": sorted(missing_once, key=lambda item: item["rank"], reverse=True),
        "confirmed_lost": sorted(confirmed_lost, key=lambda item: item["rank"], reverse=True),
    }


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
    profile_limit = int(thresholds.get("backlink_profile_limit", 500))
    profile_minimum_rank = float(thresholds.get("backlink_profile_minimum_rank", 15))
    profile_maximum_spam = float(thresholds.get("backlink_profile_maximum_spam_score", 30))
    loss_confirmations = max(2, int(thresholds.get("backlink_profile_loss_confirmations", 2)))
    profile = None

    for target in targets:
        if not budget_available(config, total_cost):
            budget_limited = True
            break
        try:
            is_primary = target["name"] == "Voyager Balloons"
            items, cost = _referring_domains(
                settings,
                target["domain"],
                limit=profile_limit if is_primary else 100,
                dofollow_only=not is_primary,
            )
            total_cost += cost
        except Exception as exc:
            failures.append({"target": target["name"], "error": str(exc)})
            continue
        if is_primary:
            profile = _update_profile(
                store,
                run_id,
                items,
                profile_minimum_rank,
                profile_maximum_spam,
                loss_confirmations,
            )
        referring_domains[target["name"]] = {
            _domain(str(item.get("domain") or "")): item
            for item in items
            if item.get("domain")
        }

    voyager_domains = set(referring_domains.get("Voyager Balloons", {}))
    excluded_domains = {primary_domain, *(_domain(item["domain"]) for item in competitors)}
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
    if profile:
        if profile["new_domains"]:
            result.alerts.append(AlertSpec(
                dedupe_key="backlink_gap:new-quality-domains",
                severity="P2",
                category="backlink_gap",
                title="Nuevos dominios de calidad enlazan a Voyager",
                message=(
                    f"El monitor ha detectado por primera vez {len(profile['new_domains'])} dominio(s) "
                    "con enlace dofollow y calidad suficiente."
                ),
                action="Verificar los enlaces, registrar la relación si procede y observar qué páginas reciben autoridad.",
                metadata={"domains": profile["new_domains"][:30]},
            ))
        for lost in profile["confirmed_lost"]:
            result.alerts.append(AlertSpec(
                dedupe_key=f"backlink_gap:lost:{lost['domain']}",
                severity="P1",
                category="backlink_gap",
                title=f"Dominio de calidad perdido: {lost['domain']}",
                message=(
                    f"DataForSEO no detecta enlaces vivos desde {lost['domain']} tras "
                    f"{lost['miss_streak']} controles consecutivos."
                ),
                action="Comprobar la página de origen y contactar solo si existía una colaboración real que merezca recuperarse.",
                evidence_url=lost["url"],
                metadata=lost,
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
    if profile is None:
        # A partial competitor response cannot prove that existing own links recovered.
        result.status = "skipped"

    result.summary = {
        "competitors": len(competitors),
        "targets_checked": len(referring_domains),
        "qualified_opportunities": len(ranked),
        "profile_baseline_initialized": bool(profile and profile["baseline_initialized"]),
        "profile_domains": profile["domains"] if profile else 0,
        "profile_dofollow_domains": profile["dofollow_domains"] if profile else 0,
        "profile_new_domains": len(profile["new_domains"]) if profile else 0,
        "profile_recovered_domains": len(profile["recovered_domains"]) if profile else 0,
        "profile_missing_once": len(profile["missing_once"]) if profile else 0,
        "profile_confirmed_lost": len(profile["confirmed_lost"]) if profile else 0,
        "failures": len(failures),
        "provider_cost_usd": round(total_cost, 4),
        "run_budget_usd": dataforseo_run_budget(config),
        "budget_limited": budget_limited,
        "alerts": len(result.alerts),
    }
    result.add_metric("qualified_opportunities", len(ranked), source="backlink_gap")
    result.add_metric("profile_domains", profile["domains"] if profile else 0, source="backlink_profile")
    result.add_metric("profile_dofollow_domains", profile["dofollow_domains"] if profile else 0, source="backlink_profile")
    result.add_metric("profile_new_domains", len(profile["new_domains"]) if profile else 0, source="backlink_profile")
    result.add_metric("profile_confirmed_lost", len(profile["confirmed_lost"]) if profile else 0, source="backlink_profile")
    result.add_metric("provider_cost_usd", total_cost, source="backlink_gap")
    return result
