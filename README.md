# Katsu VM Status Bot

A small Python Telegram bot for checking the public IP address of a VM. It uses
long polling, supports standard `HTTP_PROXY` / `HTTPS_PROXY` environment
variables, and only responds to configured Telegram user IDs.

It does not execute CMD or PowerShell commands, capture screens or keystrokes,
read Wi-Fi credentials, or install itself for automatic startup.

## Requirements

- Python 3.10 or newer
- A Telegram bot token from BotFather
- The numeric Telegram user ID(s) allowed to use the bot
- Outbound HTTPS access to Telegram and `api.ipify.org` (directly or through a proxy)

## Configure on Windows PowerShell

In the project folder, set the values for the current PowerShell session:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your-bot-token"
$env:TELEGRAM_ALLOWED_USER_IDS = "123456789"
# Optional proxy:
$env:HTTPS_PROXY = "http://proxy.example:8080"
python .\bot.py
```

Keep the token private. Do not commit `.env` files or paste tokens into chats.

## Use

Open a private chat with the bot, send `/start`, then `/getip`. The bot replies
with the public egress IP observed by the external IP service. This may be the
proxy's IP when requests go through a proxy.

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

Python's standard `urllib` honors `HTTPS_PROXY` and `HTTP_PROXY`. The proxy
must allow HTTPS access to `api.telegram.org` and `api.ipify.org`. If the proxy
requires authentication, use your organization's approved secret management;
do not commit credentials to this repository.

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
- Only `/getip`, `/start`, and `/help` are implemented.

