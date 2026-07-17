from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import requests

from .config import env_bool


def _smtp_value(primary: str, legacy: str | None = None) -> str | None:
    return os.getenv(primary) or (os.getenv(legacy) if legacy else None)


def smtp_config() -> dict[str, object]:
    username = _smtp_value("SMTP_USERNAME", "SMTP_USER")
    password = _smtp_value("SMTP_PASSWORD", "SMTP_APP_PASSWORD") or ""
    sender = os.getenv("SMTP_FROM") or username
    port = int(os.getenv("SMTP_PORT", "587"))
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "ssl": env_bool("SMTP_SSL", port == 465),
        "starttls": env_bool("SMTP_STARTTLS", port != 465),
    }


def email_configured() -> bool:
    config = smtp_config()
    return bool(os.getenv("SEO_ALERT_EMAIL_TO") and config["host"] and config["sender"])


def send_email(subject: str, body: str) -> None:
    if not email_configured():
        return
    config = smtp_config()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = str(config["sender"])
    message["To"] = os.environ["SEO_ALERT_EMAIL_TO"]
    message.set_content(body)
    smtp_class = smtplib.SMTP_SSL if config["ssl"] else smtplib.SMTP
    with smtp_class(str(config["host"]), int(config["port"]), timeout=30) as smtp:
        if config["starttls"] and not config["ssl"]:
            smtp.starttls()
        if config["username"]:
            smtp.login(str(config["username"]), str(config["password"]))
        smtp.send_message(message)


def ping_heartbeat(url: str | None) -> None:
    if not url:
        return
    response = requests.get(url, timeout=20)
    response.raise_for_status()
