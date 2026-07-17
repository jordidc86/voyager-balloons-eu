from __future__ import annotations


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
