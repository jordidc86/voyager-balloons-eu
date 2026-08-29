from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import requests

from ..config import Settings
from ..costs import budget_available, dataforseo_run_budget
from ..storage import Store
from ..types import AlertSpec, CheckResult


ENDPOINTS = {
    "chat_gpt": "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_responses/live",
    "gemini": "https://api.dataforseo.com/v3/ai_optimization/gemini/llm_responses/live",
    "perplexity": "https://api.dataforseo.com/v3/ai_optimization/perplexity/llm_responses/live",
}


def _domain(url: str | None) -> str:
    if not url:
        return ""
    return urlsplit(url).netloc.casefold().removeprefix("www.")


def _brand_target(config: dict, prompt: dict) -> tuple[str, str, list[str], set[str]]:
    brand_id = prompt.get("brand_id") or "voyager"
    brand = config.get("brands", {}).get(brand_id, {})
    name = str(brand.get("name") or config.get("brand") or "Voyager Balloons")
    aliases = [str(alias).casefold() for alias in brand.get("aliases", [name])]
    domains = brand.get("domains") or config["target_domains"]
    return brand_id, name, aliases, {
        str(domain).casefold().removeprefix("www.") for domain in domains
    }


def _brand_presence(
    response_text: str,
    citations: list[dict],
    aliases: list[str],
    domains: set[str],
) -> tuple[bool, bool]:
    normalized = response_text.casefold()
    mentioned = any(alias in normalized for alias in aliases)
    cited = any(_domain(item.get("url")) in domains for item in citations)
    return mentioned, cited


def _absence_streak(history: list, current_present: bool) -> int:
    if current_present:
        return 0
    streak = 1
    for observation in history:
        if observation.voyager_mentioned or observation.voyager_cited:
            break
        streak += 1
    return streak


def _prompt_label(prompt: dict) -> str:
    return str(prompt.get("label") or prompt.get("id") or "consulta controlada")


def _extract_response(api_result: dict) -> tuple[str, list[dict]]:
    texts: list[str] = []
    citations: list[dict] = []
    for item in api_result.get("items", []):
        if item.get("type") != "message":
            continue
        for section in item.get("sections", []):
            if section.get("text"):
                texts.append(str(section["text"]))
            for annotation in section.get("annotations") or []:
                citations.append({
                    "title": annotation.get("title"),
                    "url": annotation.get("url"),
                })
    return "\n\n".join(texts).strip(), citations


def _is_due(previous, interval_days: int, now: datetime | None = None) -> bool:
    if previous is None:
        return True
    observed_at = previous.observed_at
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - observed_at >= timedelta(days=interval_days)


def _ask(settings: Settings, provider: dict, prompt: dict) -> tuple[dict, float]:
    endpoint = ENDPOINTS[provider["name"]]
    payload = {
        "user_prompt": prompt["prompt"],
        "model_name": provider["model_name"],
        "max_output_tokens": 1200,
        "temperature": 0,
        "tag": prompt["id"],
    }
    if provider["name"] == "chat_gpt":
        payload.update({
            "web_search": True,
            "web_search_country_iso_code": prompt["country"],
            "web_search_city": prompt["city"],
        })
    elif provider["name"] == "gemini":
        payload["web_search"] = True
    elif provider["name"] == "perplexity":
        payload["web_search_country_iso_code"] = prompt["country"]
    response = requests.post(
        endpoint,
        auth=(settings.dataforseo_login or "", settings.dataforseo_password or ""),
        json=[payload],
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    task = data.get("tasks", [{}])[0]
    if task.get("status_code") != 20000:
        raise RuntimeError(task.get("status_message") or f"{provider['name']} no devolvió una tarea válida")
    api_result = task.get("result", [{}])[0]
    return api_result, float(task.get("cost") or 0)


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="ai_visibility")
    if not settings.dataforseo_login or not settings.dataforseo_password:
        result.status = "skipped"
        result.summary = {"reason": "DATAFORSEO_LOGIN/PASSWORD no configurados"}
        return result

    ai_config = config.get("ai_visibility", {})
    providers = ai_config.get("providers", [])
    prompts = ai_config.get("prompts", [])
    competitors = config.get("competitors", [])
    observations = 0
    mentions = 0
    citations_count = 0
    failures = []
    total_cost = 0.0
    budget_limited = False
    deferred = 0
    secondary_interval_days = int(config["thresholds"].get("ai_secondary_interval_days", 28))
    absence_confirmations = int(config["thresholds"].get("ai_absence_confirmations", 3))
    result.resolution_prefixes = ["ai_visibility:provider-failures"]

    for provider in providers:
        if provider.get("name") not in ENDPOINTS:
            failures.append({"provider": provider.get("name"), "error": "Proveedor no soportado"})
            continue
        for prompt in prompts:
            history = store.ai_visibility_history(
                prompt["id"],
                provider["name"],
                limit=max(1, absence_confirmations - 1),
            )
            previous = history[0] if history else None
            if prompt.get("priority") != "P0" and not _is_due(previous, secondary_interval_days):
                deferred += 1
                continue
            if not budget_available(config, total_cost):
                budget_limited = True
                break
            try:
                api_result, cost = _ask(settings, provider, prompt)
                total_cost += cost
            except Exception as exc:
                failures.append({"provider": provider["name"], "prompt_id": prompt["id"], "error": str(exc)})
                continue

            response_text, citations = _extract_response(api_result)
            brand_id, brand_name, brand_aliases, target_domains = _brand_target(config, prompt)
            brand_mentioned, brand_cited = _brand_presence(
                response_text,
                citations,
                brand_aliases,
                target_domains,
            )
            brand_present = brand_mentioned or brand_cited
            normalized = response_text.casefold()
            competitor_mentions = [
                competitor["name"]
                for competitor in competitors
                if competitor["name"].casefold() in normalized
                or competitor["domain"].casefold().removeprefix("www.") in normalized
                or any(_domain(item.get("url")) == competitor["domain"].casefold().removeprefix("www.") for item in citations)
            ]
            payload = {
                "prompt_id": prompt["id"],
                "prompt": prompt["prompt"],
                "language_code": prompt["language_code"],
                "market": prompt["market"],
                "provider": provider["name"],
                "model_name": api_result.get("model_name") or provider["model_name"],
                # Legacy column names store the prompt's target brand until a schema migration is warranted.
                "voyager_mentioned": brand_mentioned,
                "voyager_cited": brand_cited,
                "competitor_mentions": competitor_mentions,
                "citations": citations,
                "response_text": response_text,
                "web_search": api_result.get("web_search"),
                "fan_out_queries": api_result.get("fan_out_queries"),
                "brand_id": brand_id,
                "brand_name": brand_name,
            }
            store.add_ai_visibility_observation(run_id, payload)
            observations += 1
            mentions += int(brand_mentioned)
            citations_count += int(brand_cited)
            result.add_metric(
                "mentioned",
                int(brand_mentioned),
                source="ai_visibility",
                dimensions={"provider": provider["name"], "prompt_id": prompt["id"], "market": prompt["market"], "brand_id": brand_id},
            )
            result.add_metric(
                "cited",
                int(brand_cited),
                source="ai_visibility",
                dimensions={"provider": provider["name"], "prompt_id": prompt["id"], "market": prompt["market"], "brand_id": brand_id},
            )

            alert_prefix = f"ai_visibility:{provider['name']}:{prompt['id']}"
            result.resolution_prefixes.append(alert_prefix)
            absence_streak = _absence_streak(history, brand_present)
            if absence_streak >= absence_confirmations:
                result.alerts.append(AlertSpec(
                    dedupe_key=f"{alert_prefix}:absent",
                    severity="P2",
                    category="ai_visibility",
                    title=(
                        f"{brand_name} ausente en {provider['name']} · "
                        f"{prompt['market']} · {_prompt_label(prompt)}"
                    ),
                    message=(
                        f"La marca no aparece durante {absence_streak} observaciones consecutivas "
                        "para esta pregunta comercial controlada."
                    ),
                    action="Analizar empresas y fuentes citadas; reforzar la landing, datos de entidad, menciones editoriales y enlaces que alimentan esta respuesta.",
                    metadata={
                        "brand_id": brand_id,
                        "brand_name": brand_name,
                        "prompt_id": prompt["id"],
                        "prompt_label": _prompt_label(prompt),
                        "absence_streak": absence_streak,
                        "absence_confirmations": absence_confirmations,
                        "prompt": prompt["prompt"],
                        "competitors": competitor_mentions,
                        "citations": citations[:20],
                    },
                ))
            if previous and previous.voyager_cited and not brand_cited:
                result.alerts.append(AlertSpec(
                    dedupe_key=f"{alert_prefix}:citation-lost",
                    severity="P3",
                    category="ai_visibility",
                    title=f"Cita de {brand_name} perdida en {provider['name']}",
                    message=f"La web de {brand_name} dejó de aparecer como fuente para la consulta controlada de {prompt['market']}.",
                    action="Observar la siguiente medición y comparar fuentes nuevas; escalar solo si la pérdida persiste.",
                    metadata={"brand_id": brand_id, "brand_name": brand_name, "prompt": prompt["prompt"], "citations": citations[:20]},
                ))
        if budget_limited:
            break

    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="ai_visibility:provider-failures",
            severity="P1",
            category="ai_visibility",
            title="Fallos parciales en la medición de visibilidad IA",
            message=f"Fallaron {len(failures)} de {len(providers) * len(prompts)} observaciones previstas.",
            action="Revisar modelos disponibles, credenciales, saldo y límites del proveedor antes de reintentar.",
            metadata={"failures": failures[:30]},
        ))

    result.summary = {
        "observations": observations,
        "mentions": mentions,
        "citations": citations_count,
        "mention_share_percent": round((mentions / observations * 100) if observations else 0, 1),
        "citation_share_percent": round((citations_count / observations * 100) if observations else 0, 1),
        "observations_deferred": deferred,
        "failures": len(failures),
        "provider_cost_usd": round(total_cost, 4),
        "run_budget_usd": dataforseo_run_budget(config),
        "budget_limited": budget_limited,
        "alerts": len(result.alerts),
    }
    result.add_metric("observations", observations, source="ai_visibility")
    result.add_metric("mention_share_percent", result.summary["mention_share_percent"], source="ai_visibility")
    result.add_metric("citation_share_percent", result.summary["citation_share_percent"], source="ai_visibility")
    result.add_metric("provider_cost_usd", total_cost, source="ai_visibility")
    return result
