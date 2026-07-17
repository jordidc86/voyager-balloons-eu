from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Callable

from .checks import (
    ai_visibility,
    backlink_gap,
    backlinks,
    commerce,
    competitors,
    ga4,
    gsc,
    http_health,
    indexing,
    local_visibility,
    pagespeed,
    rank,
    technical,
    tracking,
)
from .config import Settings, load_config
from .costs import dataforseo_run_budget
from .notifications import send_email
from .reporting import render_markdown
from .storage import Store
from .types import AlertSpec, CheckResult


Check = Callable[..., object]

PAID_JOBS = {"rank", "local_visibility", "ai_visibility", "backlink_gap"}


JOBS: dict[str, Check] = {
    "health": http_health.run,
    "commerce": commerce.run,
    "technical": technical.run,
    "tracking": tracking.run,
    "competitors": competitors.run,
    "gsc": gsc.run,
    "indexing": indexing.run,
    "ga4": ga4.run,
    "rank": rank.run,
    "local_visibility": local_visibility.run,
    "ai_visibility": ai_visibility.run,
    "pagespeed": pagespeed.run,
    "backlinks": backlinks.run,
    "backlink_gap": backlink_gap.run,
}


def execute(job_name: str, settings: Settings, store: Store) -> tuple[object, list]:
    if job_name not in JOBS:
        raise ValueError(f"Trabajo desconocido: {job_name}")
    config = load_config(settings)
    run_id = store.start_job(job_name)
    try:
        if job_name in PAID_JOBS:
            if not settings.dataforseo_enabled:
                result = CheckResult(
                    job_name=job_name,
                    status="skipped",
                    summary={"reason": "DataForSEO pausado mediante DATAFORSEO_ENABLED"},
                )
                return result, store.save_result(run_id, result)
            now = datetime.now(timezone.utc)
            month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            budget = float(config.get("thresholds", {}).get("dataforseo_monthly_budget_usd", 25))
            spent = store.metric_sum_since("provider_cost_usd", month_start, PAID_JOBS)
            if spent >= budget:
                result = CheckResult(
                    job_name=job_name,
                    status="skipped",
                    summary={
                        "reason": "Presupuesto mensual de DataForSEO alcanzado",
                        "spent_usd": round(spent, 4),
                        "budget_usd": budget,
                    },
                )
                return result, store.save_result(run_id, result)
            configured_run_budget = dataforseo_run_budget(config)
            config["_runtime"] = {
                **config.get("_runtime", {}),
                "dataforseo_budget_remaining_usd": min(configured_run_budget, max(0.0, budget - spent)),
            }
        if job_name in {
            "gsc",
            "indexing",
            "ga4",
            "rank",
            "local_visibility",
            "ai_visibility",
            "pagespeed",
            "backlink_gap",
        }:
            result = JOBS[job_name](config, store, run_id, settings)
        else:
            result = JOBS[job_name](config, store, run_id)
        provider_cost = float(result.summary.get("provider_cost_usd", 0) or 0)
        cost_warning = float(config.get("thresholds", {}).get("dataforseo_run_cost_warning_usd", 5))
        if job_name in PAID_JOBS and provider_cost >= cost_warning:
            result.alerts.append(AlertSpec(
                dedupe_key=f"{job_name}:provider-cost-warning",
                severity="P2",
                category=job_name,
                title=f"Coste elevado en la ejecución de {job_name}",
                message=f"La ejecución consumió ${provider_cost:.2f}, por encima del umbral de ${cost_warning:.2f}.",
                action="Revisar el inventario de consultas y el coste unitario antes del siguiente ciclo.",
                metadata={"provider_cost_usd": provider_cost, "warning_usd": cost_warning},
            ))
        changed = store.save_result(run_id, result)
        urgent = [item for item in changed if item.status == "open" and item.severity in {"P0", "P1"}]
        if urgent and not settings.dry_run:
            lines = [f"{item.severity}: {item.title}\n{item.message}\nAcción: {item.action}" for item in urgent]
            send_email(f"Voyager SEO · {len(urgent)} alerta(s) urgente(s)", "\n\n".join(lines))
        return result, changed
    except Exception as exc:
        store.fail_job(run_id, traceback.format_exc())
        if not settings.dry_run:
            send_email(f"Voyager SEO · Falló {job_name}", f"{exc}\n\n{traceback.format_exc()}")
        raise


def send_digest(store: Store, settings: Settings) -> str:
    report = render_markdown(store)
    if not settings.dry_run:
        send_email("Voyager SEO · Informe semanal", report)
    return report
