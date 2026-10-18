# Lanzou Telegram Bot

Telegram bot that receives a document, uploads it to a Lanzou Cloud API, and replies with the resulting download link.

## Configuration

Create `/etc/lanzou-telegram.env` on the server:

```env
TELEGRAM_BOT_TOKEN=
LANZOU_API=http://127.0.0.1:8089/api.php
LANZOU_USER=
LANZOU_PASS=
ALLOWED_CHAT_IDS=
```

Never commit real tokens, passwords, cookies, or `.env` files.

## Install

```bash
sudo install -d -m 750 /opt/lanzou-telegram-bot
sudo install -m 750 bot.py /opt/lanzou-telegram-bot/bot.py
sudo install -m 644 lanzou-telegram.service /etc/systemd/system/lanzou-telegram.service
sudo systemctl daemon-reload
sudo systemctl enable --now lanzou-telegram.service
```
