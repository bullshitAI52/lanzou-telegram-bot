# 蓝奏云 / ImgBB Telegram 上传机器人

## 当前部署：VPS 临时文件分享

网页首页现使用 `local.html`：文件直接存到 VPS，不再经过蓝奏云。单文件最大 512 MB，总存储配额 4 GB，并保留至少约 2 GB 空闲空间。上传需要私密口令，下载使用随机链接。文件 24 小时后过期，每 10 分钟清理一次；持有链接的人都可以下载。

机器人设置 `LOCAL_UPLOAD_KEY` 后，普通文件和视频也存到 VPS；图片仍走 ImgBB。机器人当前为普通文件设置 20 MB 上限，更大的文件请使用网页。未设置此配置时保留原蓝奏云流程。当前站点使用 HTTP，不宜传输敏感内容。

后端为 `local-store.php`，文件保存在网站目录之外的 `/var/lib/lanzou-files`。Nginx 通过内部下载路径传输文件，避免长时间占用 PHP 下载进程。部署前请按实际地址修改链接配置。`deploy-local.py` 是此 VPS 的专用部署脚本，会备份并更新站点配置，不是通用安装程序。

以下为原有蓝奏云模式说明。

这是一个 Telegram 文件上传机器人。向机器人发送图片、视频或普通文件，机器人会自动上传并返回可访问的链接。

## 功能说明

- **图片上传**：Telegram 图片自动上传到 ImgBB，并返回图片链接。
- **视频上传**：Telegram 视频自动上传到蓝奏云，并返回下载地址。
- **普通文件上传**：支持文档、压缩包等文件上传到蓝奏云。
- **自动下载**：机器人先从 Telegram 下载文件，再转存到对应服务。
- **蓝奏云认证**：支持账号密码登录，也支持直接使用蓝奏云 Cookie。
- **访问限制**：可设置允许使用机器人的 Telegram 用户/聊天 ID。
- **中文提示**：上传成功、失败和登录状态都会通过 Telegram 返回。

## 使用方式

1. 在 Telegram 中打开机器人。
2. 发送 `/start`。
3. 直接发送图片、视频或文件。
4. 等待机器人返回链接。

图片走 ImgBB，视频和普通文件走蓝奏云。这样可以避免图片上传受到蓝奏云海外网络连接不稳定的影响。

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
IMGBB_API_KEY=
ALLOWED_CHAT_IDS=
```

说明：

- `IMGBB_API_KEY` 用于图片上传，API Key 只放在服务器配置中，不要提交到 GitHub。
- 设置 `LANZOU_COOKIE` 后，机器人会优先使用 Cookie，不再进行账号密码登录。
- `ALLOWED_CHAT_IDS` 用于限制可使用机器人的聊天 ID。

不要把 Telegram Bot Token、蓝奏云账号密码、Cookie 或 ImgBB API Key 提交到公开 GitHub 仓库。

## 海外 VPS 注意事项

本项目不建议使用海外 VPS 进行大文件蓝奏云上传。蓝奏云上传服务器可能出现连接超时、SSL 错误或上传到 99% 失败。

如需稳定上传，建议使用中国大陆或香港线路的 VPS。ImgBB 图片上传通常不受蓝奏云上传线路影响，但仍受 ImgBB 单文件大小限制和 API 状态影响。

## Install

```bash
sudo install -d -m 750 /opt/lanzou-telegram-bot
sudo install -m 750 bot.py /opt/lanzou-telegram-bot/bot.py
sudo install -m 644 lanzou-telegram.service /etc/systemd/system/lanzou-telegram.service
sudo systemctl daemon-reload
sudo systemctl enable --now lanzou-telegram.service
```
