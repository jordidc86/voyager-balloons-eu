from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from seo_monitor.notifications import email_configured, send_email, smtp_config


class NotificationsTests(unittest.TestCase):
    @patch("seo_monitor.notifications.smtplib.SMTP")
    @patch("seo_monitor.notifications.requests.post")
    @patch.dict(os.environ, {
        "SEO_ALERT_EMAIL_TO": "info@voyagerballoons.eu",
        "RESEND_API_KEY": "re_secret",
        "RESEND_FROM": "Voyager Balloons <info@voyagerballoons.eu>",
        "RESEND_REPLY_TO": "info@voyagerballoons.eu",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "info@voyagerballoons.eu",
    }, clear=True)
    def test_resend_is_preferred_over_smtp(self, post, smtp_class) -> None:
        self.assertTrue(email_configured())
        send_email("Prueba", "Contenido")
        post.assert_called_once()
        request = post.call_args
        self.assertEqual(request.args[0], "https://api.resend.com/emails")
        self.assertEqual(request.kwargs["json"]["to"], ["info@voyagerballoons.eu"])
        self.assertEqual(request.kwargs["json"]["reply_to"], "info@voyagerballoons.eu")
        request.return_value.raise_for_status.assert_called_once_with()
        smtp_class.assert_not_called()

    @patch.dict(os.environ, {
        "SEO_ALERT_EMAIL_TO": "info@voyagerballoons.eu",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "info@voyagerballoons.eu",
        "SMTP_APP_PASSWORD": "secret",
    }, clear=True)
    def test_existing_voyager_smtp_variable_names_are_supported(self) -> None:
        config = smtp_config()
        self.assertTrue(email_configured())
        self.assertEqual(config["username"], "info@voyagerballoons.eu")
        self.assertEqual(config["password"], "secret")
        self.assertEqual(config["sender"], "info@voyagerballoons.eu")
        self.assertTrue(config["starttls"])
        self.assertFalse(config["ssl"])

    @patch("seo_monitor.notifications.smtplib.SMTP")
    @patch.dict(os.environ, {
        "SEO_ALERT_EMAIL_TO": "info@voyagerballoons.eu",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "info@voyagerballoons.eu",
        "SMTP_APP_PASSWORD": "secret",
    }, clear=True)
    def test_send_uses_legacy_credentials_and_starttls(self, smtp_class) -> None:
        smtp = smtp_class.return_value.__enter__.return_value
        send_email("Prueba", "Contenido")
        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=30)
        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with("info@voyagerballoons.eu", "secret")
        smtp.send_message.assert_called_once()

    @patch("seo_monitor.notifications.smtplib.SMTP_SSL")
    @patch.dict(os.environ, {
        "SEO_ALERT_EMAIL_TO": "info@voyagerballoons.eu",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "465",
        "SMTP_USERNAME": "sender@example.com",
        "SMTP_PASSWORD": "secret",
    }, clear=True)
    def test_port_465_uses_implicit_tls(self, smtp_class) -> None:
        smtp = smtp_class.return_value.__enter__.return_value
        send_email("Prueba", "Contenido")
        smtp_class.assert_called_once_with("smtp.example.com", 465, timeout=30)
        smtp.starttls.assert_not_called()
