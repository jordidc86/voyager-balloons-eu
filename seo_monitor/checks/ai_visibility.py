from __future__ import annotations

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


def _ask(settings: Settings, provider: dict, prompt: dict) -> tuple[dict, float]:
    endpoint = ENDPOINTS[provider["name"]]
    payload = {
        "user_prompt": prompt["prompt"],
        "model_name": provider["model_name"],
        "max_output_tokens": 1200,
        "temperature": 0,
        "web_search": True,
        "web_search_country_iso_code": prompt["country"],
        "web_search_city": prompt["city"],
        "tag": prompt["id"],
    }
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
    target_domains = {domain.removeprefix("www.") for domain in config["target_domains"]}
    competitors = config.get("competitors", [])
    observations = 0
    mentions = 0
    citations_count = 0
    failures = []
    total_cost = 0.0
    budget_limited = False

    for provider in providers:
        if provider.get("name") not in ENDPOINTS:
            failures.append({"provider": provider.get("name"), "error": "Proveedor no soportado"})
            continue
        for prompt in prompts:
            if not budget_available(config, total_cost):
                budget_limited = True
                break
            previous = store.previous_ai_visibility(prompt["id"], provider["name"])
            try:
                api_result, cost = _ask(settings, provider, prompt)
                total_cost += cost
            except Exception as exc:
                failures.append({"provider": provider["name"], "prompt_id": prompt["id"], "error": str(exc)})
                continue

            response_text, citations = _extract_response(api_result)
            normalized = response_text.casefold()
            voyager_mentioned = "voyager balloons" in normalized or "voyagerballoons" in normalized
            voyager_cited = any(_domain(item.get("url")) in target_domains for item in citations)
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
                "voyager_mentioned": voyager_mentioned,
                "voyager_cited": voyager_cited,
                "competitor_mentions": competitor_mentions,
                "citations": citations,
                "response_text": response_text,
                "web_search": api_result.get("web_search"),
                "fan_out_queries": api_result.get("fan_out_queries"),
            }
            store.add_ai_visibility_observation(run_id, payload)
            observations += 1
            mentions += int(voyager_mentioned)
            citations_count += int(voyager_cited)
            result.add_metric(
                "mentioned",
                int(voyager_mentioned),
                source="ai_visibility",
                dimensions={"provider": provider["name"], "prompt_id": prompt["id"], "market": prompt["market"]},
            )
            result.add_metric(
                "cited",
                int(voyager_cited),
                source="ai_visibility",
                dimensions={"provider": provider["name"], "prompt_id": prompt["id"], "market": prompt["market"]},
            )

            if previous and not previous.voyager_mentioned and not voyager_mentioned:
                result.alerts.append(AlertSpec(
                    dedupe_key=f"ai_visibility:{provider['name']}:{prompt['id']}:absent",
                    severity="P2",
                    category="ai_visibility",
                    title=f"Voyager ausente en {provider['name']}: {prompt['market']}",
                    message="La marca no aparece durante dos observaciones consecutivas para una pregunta comercial controlada.",
                    action="Analizar empresas y fuentes citadas; reforzar la landing, datos de entidad, menciones editoriales y enlaces que alimentan esta respuesta.",
                    metadata={
                        "prompt": prompt["prompt"],
                        "competitors": competitor_mentions,
                        "citations": citations[:20],
                    },
                ))
        if budget_limited:
            break
            if previous and previous.voyager_cited and not voyager_cited:
                result.alerts.append(AlertSpec(
                    dedupe_key=f"ai_visibility:{provider['name']}:{prompt['id']}:citation-lost",
                    severity="P2",
                    category="ai_visibility",
                    title=f"Cita de Voyager perdida en {provider['name']}",
                    message=f"La web dejó de aparecer como fuente para la consulta controlada de {prompt['market']}.",
                    action="Comparar fuentes nuevas, comprobar cambios de indexación y actualizar la página que antes era citada.",
                    metadata={"prompt": prompt["prompt"], "citations": citations[:20]},
                ))

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
