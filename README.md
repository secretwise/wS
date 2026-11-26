# Katsu VM Status Bot

A small Python Telegram bot for checking a VM's public IP and basic read-only
system status. It uses long polling, supports standard `HTTP_PROXY` /
`HTTPS_PROXY` environment variables, and only responds to configured Telegram
user IDs.

It does not execute CMD or PowerShell commands, capture screens or keystrokes,
read Wi-Fi credentials, or install itself for automatic startup.

## Requirements

- Python 3.10 or newer
- `requests[socks]` (install with `python -m pip install -r requirements.txt`)
- A Telegram bot token from BotFather
- The numeric Telegram user ID(s) allowed to use the bot
- Outbound HTTPS access to Telegram and `api.ipify.org` (directly or through a proxy)

## Configure on Windows PowerShell

In the project folder, set the values for the current PowerShell session:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your-bot-token"
$env:TELEGRAM_ALLOWED_USER_IDS = "123456789"
# SOCKS5 proxy. Keep the credential out of source files and GitHub.
$env:TELEGRAM_PROXY_URL = "socks5h://username:password@proxy.example:1080"
python .\bot.py
```

Keep the token private. Do not commit `.env` files or paste tokens into chats.
Encode reserved characters in proxy usernames/passwords using percent encoding.

## Use

Open a private chat with the bot and send `/panel`. Available commands:

- `/getip` — public egress IP (may be the proxy's IP)
- `/status` — hostname, OS, architecture, and uptime
- `/uptime` — time since system boot
- `/disk` — free and total space on the system drive

The bot ignores messages from Telegram IDs outside
`TELEGRAM_ALLOWED_USER_IDS`. In a group, only allowlisted users can trigger
responses; for privacy, a private bot chat is recommended.

## Run checks

```powershell
python -m unittest discover -s tests -v
```

The tests use mocked responses and do not contact Telegram or the external IP
service.

## Proxy behavior

The bot routes Telegram and IP lookup requests through `TELEGRAM_PROXY_URL`
when set. For SOCKS5, use a `socks5h://` URL; DNS resolution then happens at
the proxy. The proxy must allow HTTPS access to `api.telegram.org` and
`api.ipify.org`. Do not commit proxy credentials or bot tokens to this public
repository. Prefer a secret manager or a protected per-user environment.

## Start on login

For a VM you administer, configure a visible, user-scoped task in Windows Task
Scheduler to run `python.exe <absolute-path-to-project>\bot.py` at user logon.
Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, and proxy variables in
that task's environment. Keep the task named clearly so it can be inspected and
disabled. Do not run the bot as SYSTEM unless there is a specific operational
need.

## Limitations

- `/getip` reports the public egress IP, not a private LAN or VPN interface IP.
- The IP lookup contacts `api.ipify.org`.
- The bot provides read-only diagnostics only; it has no CMD/PowerShell runner.

