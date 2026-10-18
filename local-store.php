<?php
declare(strict_types=1);
const STORE = '/var/lib/lanzou-files';
const CHUNK = 10 * 1048576;
function reply(array $data): never {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['code'=>0,'data'=>$data], JSON_UNESCAPED_UNICODE); exit;
}
function result(string $id, array $meta): array {
    return ['url'=>'http://107.172.32.153:8089/local-store.php?id='.$id,'expires'=>$meta['expires']];
}
function removeParts(string $dir): void {
    foreach (glob($dir.'/*') as $part) if (is_file($part)) unlink($part);
    @rmdir($dir);
}
function reserved(): int {
    $bytes=0;
    foreach (glob(STORE.'/*.bin') as $path) $bytes+=filesize($path);
    foreach (glob(STORE.'/parts-*') as $dir) {
        $m=json_decode((string)@file_get_contents($dir.'/manifest.json'),true);
        if ($m) $bytes+=$m['size'];
    }
    return $bytes;
}
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
foreach (glob(STORE.'/parts-*') as $dir) {
    $m=json_decode((string)@file_get_contents($dir.'/manifest.json'),true);
    if (!$m || $m['created']+86400<=time()) removeParts($dir);
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
$action=$_POST['action'] ?? 'upload';
if ($action==='init') {
    $size=filter_var($_POST['size'] ?? '',FILTER_VALIDATE_INT);
    if ($size===false || $size<0 || $size>2*1073741824) fail('文件大小无效，最大 2 GB');
    if (reserved()+$size>4*1073741824 || disk_free_space(STORE)<2*1073741824+2*$size) fail('空间不足，无法预留上传及合并空间',507);
    $id=bin2hex(random_bytes(24)); $dir=STORE.'/parts-'.$id;
    if (!mkdir($dir,0750)) fail('无法创建上传任务',500);
    $chunk=max(1048576,(int)ceil($size/10));
    $m=['name'=>basename($_POST['name'] ?? 'download'),'size'=>$size,'chunk_size'=>$chunk,'count'=>max(1,(int)ceil($size/$chunk)),'created'=>time()];
    if (file_put_contents($dir.'/manifest.json',json_encode($m))===false) fail('无法保存任务',500);
    reply(['id'=>$id,'chunk_size'=>$chunk,'count'=>$m['count']]);
}
if (in_array($action,['part','finish'],true)) {
    $id=$_POST['id'] ?? '';
    if (!preg_match('/^[a-f0-9]{48}$/D',$id)) fail('上传任务无效');
    $done=json_decode((string)@file_get_contents(STORE.'/'.$id.'.json'),true);
    if ($done) reply(result($id,$done)); // Retrying a lost completion response is safe.
    $dir=STORE.'/parts-'.$id;
    $m=json_decode((string)@file_get_contents($dir.'/manifest.json'),true);
    if (!$m) fail('上传任务已过期，请重新上传',404);
    $chunk=$m['chunk_size'] ?? CHUNK;
    if ($action==='part') {
        $index=filter_var($_POST['index'] ?? '',FILTER_VALIDATE_INT);
        if ($index===false || $index<0 || $index>=$m['count']) fail('分片编号无效');
        $f=$_FILES['file'] ?? null;
        $expected=min($chunk,$m['size']-$index*$chunk);
        if (!$f || $f['error']!==UPLOAD_ERR_OK || $f['size']!==$expected) fail('分片不完整，请重试');
        $hash=$_POST['sha256'] ?? '';
        if ($hash!=='' && !hash_equals(hash_file('sha256',$f['tmp_name']),$hash)) fail('分片校验失败');
        if (disk_free_space(STORE)<2*1073741824+$expected) fail('磁盘空间不足',507);
        if (!move_uploaded_file($f['tmp_name'],$dir.'/'.$index.'.part')) fail('分片保存失败',500);
        reply(['index'=>$index]);
    }
    for ($i=0;$i<$m['count'];$i++) {
        if (!is_file($dir.'/'.$i.'.part') || filesize($dir.'/'.$i.'.part')!==min($chunk,$m['size']-$i*$chunk)) fail('分片尚未全部上传');
    }
    if (disk_free_space(STORE)<2*1073741824+$m['size']) fail('合并空间不足',507);
    $temp=$dir.'/merged.tmp'; $out=fopen($temp,'wb');
    if (!$out) fail('无法创建合并文件',500);
    for ($i=0;$i<$m['count'];$i++) {
        $in=fopen($dir.'/'.$i.'.part','rb');
        $copied=stream_copy_to_stream($in,$out); fclose($in);
        if ($copied!==min($chunk,$m['size']-$i*$chunk)) { fclose($out); @unlink($temp); fail('合并写入失败',500); }
    }
    fclose($out);
    if (filesize($temp)!==$m['size']) fail('合并大小校验失败',500);
    $meta=['name'=>$m['name'],'size'=>$m['size'],'expires'=>time()+86400];
    if (!rename($temp,STORE.'/'.$id.'.bin')) fail('保存合并文件失败',500);
    if (file_put_contents(STORE.'/'.$id.'.json',json_encode($meta))===false) {
        unlink(STORE.'/'.$id.'.bin'); fail('保存文件信息失败',500);
    }
    removeParts($dir); reply(result($id,$meta));
}
if ($action!=='upload') fail('未知操作');
$file = $_FILES['file'] ?? null;
if (!$file || $file['error'] !== UPLOAD_ERR_OK) fail('文件未完整收到，或超过服务器限制');
if ($file['size'] > 512 * 1048576) fail('超过 512 MB 请使用网页分片上传，最大 2 GB', 413);
$used = reserved();
if ($used + $file['size'] > 4 * 1073741824 || disk_free_space(STORE) < 2 * 1073741824) fail('临时存储空间不足，请等待旧文件过期', 507);
$id = bin2hex(random_bytes(24));
$meta = ['name'=>basename($file['name']), 'size'=>$file['size'], 'expires'=>time()+86400];
if (!move_uploaded_file($file['tmp_name'], STORE . '/' . $id . '.bin')) fail('文件保存失败', 500);
if (file_put_contents(STORE . '/' . $id . '.json', json_encode($meta)) === false) {
    unlink(STORE . '/' . $id . '.bin'); fail('文件信息保存失败', 500);
}
header('Content-Type: application/json; charset=utf-8');
echo json_encode(['code'=>0, 'data'=>['url'=>'http://107.172.32.153:8089/local-store.php?id='.$id, 'expires'=>$meta['expires']]], JSON_UNESCAPED_UNICODE);
