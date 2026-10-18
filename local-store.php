<?php
declare(strict_types=1);
const STORE = '/var/lib/lanzou-files';
function fail(string $message, int $status = 400): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['code'=>1, 'msg'=>$message], JSON_UNESCAPED_UNICODE); exit;
}
// Only this application's expired files are removed, under the upload lock.
$lock = fopen(STORE . '/lock', 'c');
flock($lock, LOCK_EX);
foreach (glob(STORE . '/*.json') as $entry) {
    $meta = json_decode(file_get_contents($entry), true);
    if ($meta && $meta['expires'] <= time()) {
        @unlink(substr($entry, 0, -5) . '.bin'); @unlink($entry);
    }
}
if (PHP_SAPI === 'cli') { exit; }
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $id = $_GET['id'] ?? '';
    if (!preg_match('/^[a-f0-9]{48}$/D', $id)) fail('链接无效', 404);
    $meta = @json_decode((string)@file_get_contents(STORE . '/' . $id . '.json'), true);
    if (!$meta || !is_file(STORE . '/' . $id . '.bin')) fail('文件不存在或已过期', 404);
    header('Content-Type: application/octet-stream');
    header('X-Content-Type-Options: nosniff');
    header("Content-Disposition: attachment; filename=download; filename*=UTF-8''" . rawurlencode($meta['name']));
    header('X-Accel-Redirect: /_stored/' . $id . '.bin'); exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail('不支持此请求', 405);
$key = trim(file_get_contents('/etc/lanzou-upload.key'));
if (!$key || !hash_equals($key, $_SERVER['HTTP_X_UPLOAD_KEY'] ?? ($_POST['key'] ?? ''))) fail('上传口令不正确', 403);
$file = $_FILES['file'] ?? null;
if (!$file || $file['error'] !== UPLOAD_ERR_OK) fail('文件未完整收到，或超过服务器限制');
if ($file['size'] > 512 * 1048576) fail('单个文件最大 512 MB', 413);
$used = 0;
foreach (glob(STORE . '/*.bin') as $path) $used += filesize($path);
if ($used + $file['size'] > 4 * 1073741824 || disk_free_space(STORE) < 2 * 1073741824) fail('临时存储空间不足，请等待旧文件过期', 507);
$id = bin2hex(random_bytes(24));
$meta = ['name'=>basename($file['name']), 'size'=>$file['size'], 'expires'=>time()+86400];
if (!move_uploaded_file($file['tmp_name'], STORE . '/' . $id . '.bin')) fail('文件保存失败', 500);
if (file_put_contents(STORE . '/' . $id . '.json', json_encode($meta)) === false) {
    unlink(STORE . '/' . $id . '.bin'); fail('文件信息保存失败', 500);
}
header('Content-Type: application/json; charset=utf-8');
echo json_encode(['code'=>0, 'data'=>['url'=>'http://107.172.32.153:8089/local-store.php?id='.$id, 'expires'=>$meta['expires']]], JSON_UNESCAPED_UNICODE);
