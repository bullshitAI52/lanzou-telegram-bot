#!/usr/bin/env python3
import json, os, sys, tempfile, time, urllib.parse, urllib.request, uuid

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
API = os.environ.get('LANZOU_API', 'http://127.0.0.1:8089/api.php')
USER = os.environ.get('LANZOU_USER', '').strip()
PASS = os.environ.get('LANZOU_PASS', '').strip()
COOKIE = os.environ.get('LANZOU_COOKIE', '').strip()
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', '').strip()
LOCAL_UPLOAD_KEY = os.environ.get('LOCAL_UPLOAD_KEY', '').strip()
ALLOWED = {x.strip() for x in os.environ.get('ALLOWED_CHAT_IDS', '').split(',') if x.strip()}

if not TOKEN:
    print('TELEGRAM_BOT_TOKEN is not configured', file=sys.stderr); sys.exit(2)

def tg(method, data=None):
    url = f'https://api.telegram.org/bot{TOKEN}/{method}'
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data or {}).encode(), method='POST')
    with urllib.request.urlopen(req, timeout=90) as r: return json.loads(r.read())

def send(chat, text):
    tg('sendMessage', {'chat_id': chat, 'text': text})

def multipart(url, fields, path, file_field='file'):
    boundary = '----lanzou' + uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    name = os.path.basename(path)
    body += f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
    with open(path, 'rb') as f:
        while chunk := f.read(1024 * 1024): body += chunk
    body += f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req, timeout=3600) as r: return json.loads(r.read())

def lanzou_login():
    req = urllib.request.Request(API + '?action=login', data=urllib.parse.urlencode({'user': USER, 'pass': PASS}).encode())
    with urllib.request.urlopen(req, timeout=300) as r:
        obj = json.loads(r.read())
    return obj.get('data', {}).get('cookie_str', '')

def upload(path, cookie):
    return multipart(API + '?action=upload', {'cookie': cookie, 'folder_name': ''}, path)

def imgbb_upload(path):
    if not IMGBB_API_KEY:
        raise RuntimeError('IMGBB_API_KEY is not configured')
    out = multipart('https://api.imgbb.com/1/upload', {'key': IMGBB_API_KEY}, path, 'image')
    if out.get('success') and out.get('data'):
        data = out['data']
        return data.get('display_url') or data.get('url') or data.get('image', {}).get('url')
    raise RuntimeError(out.get('error', {}).get('message') or str(out))

def main():
    offset = 0
    cookie = COOKIE
    while True:
        try:
            result = tg('getUpdates', {'timeout': 50, 'offset': offset})
            for u in result.get('result', []):
                offset = u['update_id'] + 1
                msg = u.get('message') or {}
                chat = str((msg.get('chat') or {}).get('id', ''))
                if not chat or (ALLOWED and chat not in ALLOWED): continue
                if msg.get('text', '').strip() == '/start':
                    send(chat, '图片上传到 ImgBB；视频和文件临时保存到服务器，链接有效期 24 小时。大文件请使用网页 http://107.172.32.153:8089/')
                    continue
                doc = msg.get('document')
                if doc:
                    file_id = doc['file_id']
                    file_name = doc.get('file_name', 'file.bin')
                elif msg.get('video'):
                    video = msg['video']
                    file_id = video['file_id']
                    file_name = video.get('file_name') or f"video-{video.get('file_unique_id', 'upload')}.mp4"
                elif msg.get('photo'):
                    photo = msg['photo'][-1]
                    file_id = photo['file_id']
                    file_name = f"photo-{photo.get('file_unique_id', 'upload')}.jpg"
                else:
                    send(chat, '请发送图片、视频或文件。'); continue
                send(chat, '已收到文件，正在上传，请稍候……')
                is_photo = bool(msg.get('photo'))
                if is_photo:
                    try:
                        info = tg('getFile', {'file_id': file_id})['result']
                        with tempfile.TemporaryDirectory(prefix='imgbb-tg-') as td:
                            path = os.path.join(td, file_name)
                            urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{info["file_path"]}', path)
                            link = imgbb_upload(path)
                        send(chat, '图片上传成功：\n' + link)
                    except Exception as e:
                        print('ImgBB upload failed:', repr(e), file=sys.stderr)
                        send(chat, '图片上传失败：' + str(e))
                    continue
                if LOCAL_UPLOAD_KEY:
                    try:
                        item = doc or msg.get('video') or {}
                        if item.get('file_size', 0) > 20 * 1048576:
                            send(chat, '此机器人的 Telegram 文件下载通道限制为 20 MB，大文件请使用网页：http://107.172.32.153:8089/')
                            continue
                        info = tg('getFile', {'file_id': file_id})['result']
                        with tempfile.TemporaryDirectory(prefix='vps-tg-') as td:
                            path = os.path.join(td, os.path.basename(file_name))
                            urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{info["file_path"]}', path)
                            out = multipart('http://127.0.0.1:8089/local-store.php', {'key': LOCAL_UPLOAD_KEY}, path)
                        if out.get('code') != 0:
                            raise RuntimeError(out.get('msg', '保存失败'))
                        send(chat, '上传成功，链接有效期 24 小时：\n' + out['data']['url'])
                    except Exception:
                        send(chat, '文件保存失败，请重试或使用网页上传。')
                    continue
                if not cookie:
                    if not (USER and PASS):
                        send(chat, '蓝奏云账号尚未配置，暂时无法上传。'); continue
                    send(chat, '正在登录蓝奏云，首次上传可能需要稍候……')
                    try:
                        cookie = lanzou_login()
                    except Exception as e:
                        print('Lanzou login failed:', repr(e), file=sys.stderr)
                        send(chat, '蓝奏云登录超过 5 分钟仍未完成或失败，请稍后重试。')
                        continue
                    if not cookie:
                        send(chat, '蓝奏云登录失败，请检查账号或密码。'); continue
                info = tg('getFile', {'file_id': file_id})['result']
                with tempfile.TemporaryDirectory(prefix='lanzou-tg-') as td:
                    path = os.path.join(td, file_name)
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
