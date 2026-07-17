import os
import unittest
from unittest.mock import patch

from seo_monitor.config import Settings


class SeoMonitorSettingsTests(unittest.TestCase):
    def test_dataforseo_is_enabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(Settings.from_env().dataforseo_enabled)

    def test_dataforseo_can_be_paused_without_removing_credentials(self):
        env = {
            "DATAFORSEO_ENABLED": "false",
            "DATAFORSEO_LOGIN": "api-user",
            "DATAFORSEO_PASSWORD": "api-password",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings.from_env()
        self.assertFalse(settings.dataforseo_enabled)
        self.assertEqual(settings.dataforseo_login, "api-user")
        self.assertEqual(settings.dataforseo_password, "api-password")


if __name__ == "__main__":
    unittest.main()
