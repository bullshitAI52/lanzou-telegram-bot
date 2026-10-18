#!/usr/bin/env python3
import json, os, sys, tempfile, time, urllib.parse, urllib.request, uuid

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
API = os.environ.get('LANZOU_API', 'http://127.0.0.1:8089/api.php')
USER = os.environ.get('LANZOU_USER', '').strip()
PASS = os.environ.get('LANZOU_PASS', '').strip()
ALLOWED = {x.strip() for x in os.environ.get('ALLOWED_CHAT_IDS', '').split(',') if x.strip()}

if not TOKEN:
    print('TELEGRAM_BOT_TOKEN is not configured', file=sys.stderr); sys.exit(2)

def tg(method, data=None):
    url = f'https://api.telegram.org/bot{TOKEN}/{method}'
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data or {}).encode(), method='POST')
    with urllib.request.urlopen(req, timeout=90) as r: return json.loads(r.read())

def send(chat, text):
    tg('sendMessage', {'chat_id': chat, 'text': text})

def multipart(url, fields, path):
    boundary = '----lanzou' + uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    name = os.path.basename(path)
    body += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
    with open(path, 'rb') as f:
        while chunk := f.read(1024 * 1024): body += chunk
    body += f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req, timeout=3600) as r: return json.loads(r.read())

def lanzou_login():
    req = urllib.request.Request(API + '?action=login', data=urllib.parse.urlencode({'user': USER, 'pass': PASS}).encode())
    with urllib.request.urlopen(req, timeout=120) as r:
        obj = json.loads(r.read())
    return obj.get('data', {}).get('cookie_str', '')

def upload(path, cookie):
    return multipart(API + '?action=upload', {'cookie': cookie, 'folder_name': ''}, path)

def main():
    offset = 0
    cookie = ''
    while True:
        try:
            result = tg('getUpdates', {'timeout': 50, 'offset': offset})
            for u in result.get('result', []):
                offset = u['update_id'] + 1
                msg = u.get('message') or {}
                chat = str((msg.get('chat') or {}).get('id', ''))
                if not chat or (ALLOWED and chat not in ALLOWED): continue
                if msg.get('text', '').strip() == '/start':
                    send(chat, '发送文件，我会自动上传到蓝奏云并返回下载地址。')
                    continue
                doc = msg.get('document')
                if not doc:
                    send(chat, '请直接发送文件。'); continue
                send(chat, '已收到文件，正在上传，请稍候……')
                if not cookie:
                    if not (USER and PASS):
                        send(chat, '蓝奏云账号尚未配置，暂时无法上传。'); continue
                    send(chat, '正在登录蓝奏云，首次上传可能需要稍候……')
                    cookie = lanzou_login()
                    if not cookie:
                        send(chat, '蓝奏云登录失败，请检查账号或密码。'); continue
                info = tg('getFile', {'file_id': doc['file_id']})['result']
                with tempfile.TemporaryDirectory(prefix='lanzou-tg-') as td:
                    path = os.path.join(td, doc.get('file_name', 'file.bin'))
                    urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{info["file_path"]}', path)
                    out = upload(path, cookie)
                if out.get('code') == 0:
                    data = out.get('data') or {}
                    link = data.get('url') or data.get('download_url') or data.get('share_url')
                    send(chat, '上传成功：\n' + (link or json.dumps(data, ensure_ascii=False)))
                else: send(chat, '上传失败：' + str(out.get('msg', out)))
        except Exception as e:
            print(repr(e), file=sys.stderr); time.sleep(5)

if __name__ == '__main__': main()
