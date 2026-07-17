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
    resend_ready = bool(os.getenv("RESEND_API_KEY") and os.getenv("RESEND_FROM"))
    smtp_ready = bool(config["host"] and config["sender"])
    return bool(os.getenv("SEO_ALERT_EMAIL_TO") and (resend_ready or smtp_ready))


def _send_with_resend(subject: str, body: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("RESEND_FROM")
    if not api_key or not sender:
        return False
    payload = {
        "from": sender,
        "to": [os.environ["SEO_ALERT_EMAIL_TO"]],
        "subject": subject,
        "text": body,
    }
    if reply_to := os.getenv("RESEND_REPLY_TO"):
        payload["reply_to"] = reply_to
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return True


def send_email(subject: str, body: str) -> None:
    if not email_configured():
        return
    if _send_with_resend(subject, body):
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
