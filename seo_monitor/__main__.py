from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import Settings, load_config, load_keywords
from .notifications import email_configured
from .reporting import render_markdown
from .runner import JOBS, execute
from .storage import Store
from .worker import run_due_once, run_forever


def doctor(settings: Settings, store: Store) -> int:
    config = load_config(settings)
    keywords = load_keywords(settings)
    checks = {
        "database": "ok",
        "config": str(settings.config_path),
        "strategic_pages": len(config.get("strategic_pages", [])),
        "competitors": len(config.get("competitors", [])),
        "local_visibility_checks": len(config.get("local_visibility", {}).get("checks", [])),
        "ai_visibility_observations_per_run": (
            len(config.get("ai_visibility", {}).get("providers", []))
            * len(config.get("ai_visibility", {}).get("prompts", []))
        ),
        "tracking_checks": 7 if config.get("tracking") else 0,
        "keywords": len(keywords),
        "dataforseo_monthly_budget_usd": config.get("thresholds", {}).get("dataforseo_monthly_budget_usd"),
        "google_credentials": bool(settings.google_service_account_json),
        "gsc_property": settings.gsc_property,
        "ga4_property": bool(settings.ga4_property_id),
        "dataforseo": bool(settings.dataforseo_login and settings.dataforseo_password),
        "pagespeed": bool(settings.pagespeed_api_key),
        "email_destination": bool(settings.alert_email_to),
        "email_transport": email_configured(),
        "heartbeat": bool(settings.heartbeat_url),
        "dry_run": settings.dry_run,
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m seo_monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("job", choices=[*JOBS, "all"])
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--output")
    subparsers.add_parser("worker")
    subparsers.add_parser("tick")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    store = Store(settings.database_url)
    store.initialize()

    if args.command == "doctor":
        return doctor(settings, store)
    if args.command == "report":
        report = render_markdown(store)
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
        else:
            print(report)
        return 0
    if args.command == "worker":
        run_forever(settings, store)
        return 0
    if args.command == "tick":
        summary = run_due_once(settings, store)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if summary["failed"] else 0

    jobs = list(JOBS) if args.job == "all" else [args.job]
    exit_code = 0
    for job_name in jobs:
        try:
            result, changed = execute(job_name, settings, store)
            print(json.dumps({
                "job": job_name,
                "status": result.status,
                "summary": result.summary,
                "open_alerts_in_run": len(result.alerts),
                "changed_alerts": len(changed),
            }, ensure_ascii=False, indent=2))
        except Exception as exc:
            print(json.dumps({"job": job_name, "status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
