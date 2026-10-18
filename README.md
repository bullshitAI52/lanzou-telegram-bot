# Lanzou Telegram Bot

Telegram bot that receives a document, uploads it to a Lanzou Cloud API, and replies with the resulting download link.

## Deployment warning

This project is **not recommended for overseas VPS deployments** when uploading large files. Lanzou Cloud's upload endpoints (especially `pc.woozooo.com`) may be slow or unreachable from foreign networks, causing SSL timeouts, chunk retries, and failed uploads.

For reliable uploads, use a VPS with a stable mainland China or Hong Kong route to Lanzou Cloud. Overseas servers are more suitable for link parsing and API experiments; large-file upload reliability is not guaranteed.

## Configuration

Create `/etc/lanzou-telegram.env` on the server:

```env
TELEGRAM_BOT_TOKEN=
LANZOU_API=http://127.0.0.1:8089/api.php
LANZOU_USER=
LANZOU_PASS=
LANZOU_COOKIE=
ALLOWED_CHAT_IDS=
```

When `LANZOU_COOKIE` is set, the bot skips the account-password login.

Never commit real tokens, passwords, cookies, or `.env` files.

## Install

```bash
sudo install -d -m 750 /opt/lanzou-telegram-bot
sudo install -m 750 bot.py /opt/lanzou-telegram-bot/bot.py
sudo install -m 644 lanzou-telegram.service /etc/systemd/system/lanzou-telegram.service
sudo systemctl daemon-reload
sudo systemctl enable --now lanzou-telegram.service
```
