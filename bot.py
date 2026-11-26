"""Minimal Telegram bot for reporting this VM's public IP address.

The bot does not execute operating-system commands or collect credentials.
Configure HTTPS_PROXY/HTTP_PROXY in the environment when a proxy is needed.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import sys
import time
from pathlib import Path

import requests


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
    response = requests.post(
        url,
        data=params,
        timeout=POLL_TIMEOUT + 15,
        proxies=get_proxy_config(),
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API returned an error for {method}")
    return result


def get_public_ip() -> str:
    response = requests.get(
        IP_URL,
        headers={"User-Agent": "katsu-vm-status/1.0"},
        timeout=15,
        proxies=get_proxy_config(),
    )
    response.raise_for_status()
    result = response.json()
    ip = result.get("ip")
    if not isinstance(ip, str) or not ip:
        raise RuntimeError("IP service returned an invalid response")
    return ip


def get_proxy_config() -> dict[str, str] | None:
    proxy_url = os.environ.get("TELEGRAM_PROXY_URL", "").strip()
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def format_duration(seconds: int) -> str:
    days, remainder = divmod(max(0, seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} дн.")
    if hours or days:
        parts.append(f"{hours} ч.")
    if minutes or hours or days:
        parts.append(f"{minutes} мин.")
    parts.append(f"{seconds} сек.")
    return " ".join(parts)


def get_uptime() -> str:
    # monotonic time is measured from system boot on supported Python platforms.
    return format_duration(int(time.monotonic()))


def get_status() -> str:
    return (
        f"Машина: {socket.gethostname()}\n"
        f"ОС: {platform.system()} {platform.release()}\n"
        f"Архитектура: {platform.machine()}\n"
        f"Время работы: {get_uptime()}"
    )


def get_disk_status() -> str:
    root = Path.home().anchor or os.path.abspath(os.sep)
    usage = shutil.disk_usage(root)
    total_gb = usage.total / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    return f"Диск {root}: свободно {free_gb:.1f} ГБ из {total_gb:.1f} ГБ"


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
                if command in ("/start", "/help", "/panel"):
                    send_message(
                        token,
                        chat_id,
                        "Панель диагностики VM:\n/getip — внешний IP\n/status — система и хост\n"
                        "/uptime — время работы\n/disk — свободное место\n\n"
                        "Выполнение командной строки не поддерживается.",
                    )
                elif command == "/getip":
                    try:
                        ip = get_public_ip()
                        send_message(token, chat_id, f"Публичный IP этой машины: {ip}")
                    except (OSError, ValueError, RuntimeError):
                        send_message(token, chat_id, "Не удалось получить публичный IP.")
                elif command == "/status":
                    send_message(token, chat_id, get_status())
                elif command == "/uptime":
                    send_message(token, chat_id, f"Время работы системы: {get_uptime()}")
                elif command == "/disk":
                    try:
                        send_message(token, chat_id, get_disk_status())
                    except OSError:
                        send_message(token, chat_id, "Не удалось прочитать состояние диска.")
                # Unknown commands are intentionally ignored. No shell or subprocess interface.
        except (requests.RequestException, OSError, TimeoutError, ValueError, RuntimeError) as exc:
            print(f"Temporary network/API error: {type(exc).__name__}", file=sys.stderr, flush=True)
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)

