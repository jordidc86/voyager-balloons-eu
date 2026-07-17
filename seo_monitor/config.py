from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _path_from_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else ROOT / value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    config_path: Path
    keywords_path: Path
    google_service_account_json: str | None
    gsc_property: str
    ga4_property_id: str | None
    dataforseo_login: str | None
    dataforseo_password: str | None
    pagespeed_api_key: str | None
    alert_email_to: str | None
    heartbeat_url: str | None
    poll_seconds: int
    dry_run: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "SEO_MONITOR_DATABASE_URL",
                "sqlite:///data/seo-monitor/seo-monitor.db",
            ),
            config_path=_path_from_env("SEO_MONITOR_CONFIG", "config/seo-monitor.json"),
            keywords_path=_path_from_env("SEO_MONITOR_KEYWORDS", "config/strategic-keywords.csv"),
            google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or None,
            gsc_property=os.getenv("GSC_PROPERTY", "sc-domain:voyagerballoons.eu"),
            ga4_property_id=os.getenv("GA4_PROPERTY_ID") or None,
            dataforseo_login=os.getenv("DATAFORSEO_LOGIN") or None,
            dataforseo_password=os.getenv("DATAFORSEO_PASSWORD") or None,
            pagespeed_api_key=os.getenv("PAGESPEED_API_KEY") or None,
            alert_email_to=os.getenv("SEO_ALERT_EMAIL_TO") or None,
            heartbeat_url=os.getenv("SEO_MONITOR_HEARTBEAT_URL") or None,
            poll_seconds=max(15, int(os.getenv("SEO_MONITOR_POLL_SECONDS", "60"))),
            dry_run=env_bool("SEO_MONITOR_DRY_RUN"),
        )


def load_config(settings: Settings) -> dict[str, Any]:
    return json.loads(settings.config_path.read_text(encoding="utf-8"))


def load_keywords(settings: Settings) -> list[dict[str, str]]:
    with settings.keywords_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
