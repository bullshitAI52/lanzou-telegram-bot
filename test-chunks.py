import concurrent.futures, hashlib, json, pathlib, subprocess, tempfile
BASE='http://127.0.0.1:8089/local-store.php'
KEY=pathlib.Path('/etc/lanzou-upload.key').read_text().strip()
def call(fields, part=None, expected=0):
    args=['curl','-sS','--max-time','180','-H','X-Upload-Key: '+KEY]
    for k,v in fields.items(): args+=['-F',f'{k}={v}']
    if part is not None: args+=['-F','file=@'+str(part)]
    obj=json.loads(subprocess.check_output(args+[BASE]))
    assert obj['code']==expected,obj
    return obj.get('data',{})
with tempfile.TemporaryDirectory() as tmp:
    size=110*1048576+123
    task=call({'action':'init','name':'测试110MB.bin','size':size})
    ident=task['id']; count=task['count']; digest=hashlib.sha256(); paths=[]
    for i in range(count):
        data=bytes([i])*min(task['chunk_size'],size-i*task['chunk_size'])
        digest.update(data); p=pathlib.Path(tmp)/str(i);p.write_bytes(data);paths.append(p)
    call({'action':'finish','id':ident},expected=1)
    call({'action':'part','id':ident,'index':0,'sha256':'bad'},paths[0],expected=1)
    def upload(i):
        return call({'action':'part','id':ident,'index':i,'sha256':hashlib.sha256(paths[i].read_bytes()).hexdigest()},paths[i])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(upload,reversed(range(count))))
    upload(0)
    first=call({'action':'finish','id':ident})
    second=call({'action':'finish','id':ident})
    assert first==second
    download=pathlib.Path(tmp)/'result'
    subprocess.run(['curl','-fsS','-o',str(download),BASE+'?id='+ident],check=True)
    assert download.stat().st_size==size
    actual=hashlib.sha256()
    with download.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):actual.update(block)
    assert actual.digest()==digest.digest()
    assert not pathlib.Path('/var/lib/lanzou-files/parts-'+ident).exists()
    for ext in ['.bin','.json']:pathlib.Path('/var/lib/lanzou-files/'+ident+ext).unlink()
    print('PASS: 110MB+123 bytes, 12 parts, two workers, out-of-order delivery, duplicate part, missing part rejection, hash rejection, idempotent completion, download SHA256, part cleanup. Test data removed.')
