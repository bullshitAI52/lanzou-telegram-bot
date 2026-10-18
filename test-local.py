import tempfile, pathlib, subprocess, json, hashlib
base = 'http://127.0.0.1:8089'
with tempfile.TemporaryDirectory(prefix='vps-upload-test-') as tmp:
    src = pathlib.Path(tmp) / 'test-110MB.bin'
    with src.open('wb') as f:
        for _ in range(110): f.write(b'X' * 1048576)
    key = pathlib.Path('/etc/lanzou-upload.key').read_text().strip()
    result = subprocess.check_output(['curl','-fsS','--max-time','180','-H','X-Upload-Key: '+key,'-F','file=@'+str(src),base+'/local-store.php'])
    out = json.loads(result)
    assert out['code'] == 0, out
    query = out['data']['url'].split('?',1)[1]
    dst = pathlib.Path(tmp) / 'download.bin'
    subprocess.run(['curl','-fsS','--max-time','180','-o',str(dst),base+'/local-store.php?'+query],check=True)
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as f:
            for data in iter(lambda:f.read(1048576),b''): h.update(data)
        return h.digest()
    assert digest(src)==digest(dst)
    print('110 MB upload and download: PASS; SHA256 matches')
    code=subprocess.check_output(['curl','-sS','-o','/dev/null','-w','%{http_code}','-X','POST',base+'/local-store.php']).decode()
    assert code=='403', code
    print('Unauthenticated upload rejected: PASS')
    token=query.split('=',1)[1]
    for suffix in ['.bin','.json']:
        (pathlib.Path('/var/lib/lanzou-files')/(token+suffix)).unlink()
    print('Test files removed')
