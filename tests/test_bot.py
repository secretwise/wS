import unittest
from unittest.mock import Mock, patch

import bot


class BotTests(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(bot.format_duration(90061), "1 дн. 1 ч. 1 мин. 1 сек.")

    def test_public_ip_response_is_parsed(self):
        response = Mock()
        response.json.return_value = {"ip": "203.0.113.10"}
        with patch.object(bot.requests, "get", return_value=response):
            self.assertEqual(bot.get_public_ip(), "203.0.113.10")

    def test_socks_proxy_configuration_is_read_from_environment(self):
        proxy = "socks5h://user:pass@proxy.example:1080"
        with patch.dict("os.environ", {"TELEGRAM_PROXY_URL": proxy}):
            self.assertEqual(bot.get_proxy_config(), {"http": proxy, "https": proxy})

    def test_empty_and_non_allowlisted_updates_are_ignored(self):
        updates = [
            {"update_id": 1, "message": {"from": {"id": 42}, "chat": {"id": 42}, "text": ""}},
            {"update_id": 2, "message": {"from": {"id": 99}, "chat": {"id": 99}, "text": "/getip"}},
            {"update_id": 3, "message": {"from": {"id": 42}, "chat": {"id": 42}, "text": "/getip"}},
        ]
        calls = 0

        def fake_telegram_request(_token, method, _params):
            nonlocal calls
            if method != "getUpdates":
                self.fail(f"Unexpected Telegram method: {method}")
            calls += 1
            if calls == 1:
                return {"result": updates}
            raise KeyboardInterrupt

        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_ALLOWED_USER_IDS": "42",
        }), patch.object(bot, "telegram_request", side_effect=fake_telegram_request), \
             patch.object(bot, "get_public_ip", return_value="203.0.113.10"), \
             patch.object(bot, "send_message") as send:
            with self.assertRaises(KeyboardInterrupt):
                bot.main()

        send.assert_called_once_with("test-token", 42, "Публичный IP этой машины: 203.0.113.10")


if __name__ == "__main__":
    unittest.main()

