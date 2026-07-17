from __future__ import annotations

from typing import Any

import requests


DATAFORSEO_USER_DATA_ENDPOINT = "https://api.dataforseo.com/v3/appendix/user_data"


def dataforseo_account_budget(settings: Any) -> dict[str, float | str]:
    """Return the provider balance and current daily spend without charge."""
    response = requests.get(
        DATAFORSEO_USER_DATA_ENDPOINT,
        auth=(settings.dataforseo_login or "", settings.dataforseo_password or ""),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    task = data.get("tasks", [{}])[0]
    if task.get("status_code") != 20000:
        raise RuntimeError(task.get("status_message") or "DataForSEO no devolvio los datos de cuenta")
    account = task.get("result", [{}])[0]
    money = account.get("money") or {}
    limits = money.get("limits") or {}
    statistics = money.get("statistics") or {}
    day_limit = (limits.get("day") or {}).get("total") or 0
    day_stats = statistics.get("day") or {}
    return {
        "balance": float(money.get("balance") or 0),
        "day_limit_usd": float(day_limit),
        "day_spent_usd": float(day_stats.get("total") or 0),
        "day": str(day_stats.get("value") or ""),
    }


def dataforseo_run_budget(config: dict) -> float:
    runtime = config.get("_runtime", {})
    thresholds = config.get("thresholds", {})
    return max(
        0.0,
        float(runtime.get(
            "dataforseo_budget_remaining_usd",
            thresholds.get("dataforseo_run_budget_usd", 5),
        )),
    )


def budget_available(config: dict, spent_in_run: float) -> bool:
    return spent_in_run < dataforseo_run_budget(config)
