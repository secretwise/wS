"""Minimal Telegram bot for reporting this VM's public IP address.

The bot does not execute operating-system commands or collect credentials.
Configure HTTPS_PROXY/HTTP_PROXY in the environment when a proxy is needed.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://api.telegram.org/bot{token}/{method}"
IP_URL = "https://api.ipify.org?format=json"
POLL_TIMEOUT = 30


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def telegram_request(token: str, method: str, params: dict[str, object]) -> dict:
    url = API_BASE.format(token=token, method=method)
    body = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(request, timeout=POLL_TIMEOUT + 15) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API returned an error for {method}")
    return result


def get_public_ip() -> str:
    request = urllib.request.Request(IP_URL, headers={"User-Agent": "katsu-vm-status/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
    ip = result.get("ip")
    if not isinstance(ip, str) or not ip:
        raise RuntimeError("IP service returned an invalid response")
    return ip


def send_message(token: str, chat_id: int, text: str) -> None:
    telegram_request(token, "sendMessage", {"chat_id": chat_id, "text": text})


def main() -> None:
    token = required_env("TELEGRAM_BOT_TOKEN")
    allowed_ids = {
        int(item.strip())
        for item in required_env("TELEGRAM_ALLOWED_USER_IDS").split(",")
        if item.strip()
    }
    if not allowed_ids:
        raise RuntimeError("TELEGRAM_ALLOWED_USER_IDS must contain at least one numeric ID")

    print("Katsu VM Status Bot is running. Allowed Telegram IDs are configured.", flush=True)
    next_offset: int | None = None
    while True:
        try:
            params: dict[str, object] = {"timeout": POLL_TIMEOUT}
            if next_offset is not None:
                params["offset"] = next_offset
            updates = telegram_request(token, "getUpdates", params).get("result", [])
            for update in updates:
                next_offset = int(update["update_id"]) + 1
                message = update.get("message") or update.get("channel_post") or {}
                sender = message.get("from") or {}
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                sender_id = sender.get("id")
                command_parts = (message.get("text") or "").strip().split(maxsplit=1)
                if not command_parts:
                    continue
                command = command_parts[0].lower()

                if sender_id not in allowed_ids or not isinstance(chat_id, int):
                    continue
                if command in ("/start", "/help"):
                    send_message(token, chat_id, "Доступные команды: /getip")
                elif command == "/getip":
                    try:
                        ip = get_public_ip()
                        send_message(token, chat_id, f"Публичный IP этой машины: {ip}")
                    except (OSError, ValueError, RuntimeError):
                        send_message(token, chat_id, "Не удалось получить публичный IP.")
                # Unknown commands are intentionally ignored. No shell or subprocess interface.
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as exc:
            print(f"Temporary network/API error: {type(exc).__name__}", file=sys.stderr, flush=True)
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)

