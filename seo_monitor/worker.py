from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from .config import Settings, load_config
from .notifications import ping_heartbeat
from .runner import JOBS, execute, send_digest
from .storage import Store


LOGGER = logging.getLogger("voyager-seo-monitor")


def _due(last_run, interval_seconds: int) -> bool:
    if last_run is None:
        return True
    observed = last_run.started_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    effective_interval = interval_seconds
    if last_run.status == "failed":
        effective_interval = min(interval_seconds, 3600)
    elif last_run.status == "skipped":
        effective_interval = min(interval_seconds, 21600)
    return (datetime.now(timezone.utc) - observed).total_seconds() >= effective_interval


def run_due_once(settings: Settings, store: Store) -> dict[str, int]:
    stale_runs = store.fail_stale_runs(datetime.now(timezone.utc) - timedelta(hours=2))
    if stale_runs:
        LOGGER.warning("recovered %s stale job run(s)", stale_runs)
    config = load_config(settings)
    schedules = config["schedules_seconds"]
    completed = 0
    failed = 0
    skipped_due = 0
    for job_name in JOBS:
        if not _due(store.latest_run(job_name), int(schedules[job_name])):
            skipped_due += 1
            continue
        try:
            result, changed = execute(job_name, settings, store)
            completed += 1
            LOGGER.info("job=%s status=%s alerts=%s changed=%s", job_name, result.status, len(result.alerts), len(changed))
        except Exception:
            failed += 1
            LOGGER.exception("job=%s failed", job_name)

    if _due(store.latest_run("digest"), int(schedules["digest"])):
        run_id = store.start_job("digest")
        try:
            report = send_digest(store, settings)
            from .types import CheckResult
            store.save_result(run_id, CheckResult(job_name="digest", summary={"characters": len(report)}))
            completed += 1
        except Exception:
            failed += 1
            LOGGER.exception("digest failed")
            store.fail_job(run_id, "No se pudo generar o enviar el informe")

    if failed == 0:
        try:
            ping_heartbeat(settings.heartbeat_url)
        except Exception:
            failed += 1
            LOGGER.exception("heartbeat ping failed")
    else:
        LOGGER.warning("heartbeat omitted because the cycle had %s failure(s)", failed)
    return {"completed": completed, "failed": failed, "not_due": skipped_due, "stale_recovered": stale_runs}


def run_forever(settings: Settings, store: Store) -> None:
    LOGGER.info("Voyager SEO worker started")
    while True:
        run_due_once(settings, store)
        time.sleep(settings.poll_seconds)
