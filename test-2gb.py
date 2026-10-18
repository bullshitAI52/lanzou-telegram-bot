import hashlib, json, pathlib, subprocess, tempfile
BASE='http://127.0.0.1:8089/local-store.php'
KEY=pathlib.Path('/etc/lanzou-upload.key').read_text().strip()
def call(fields, part=None, expected=0):
    args=['curl','-sS','--max-time','300','-H','X-Upload-Key: '+KEY]
    for k,v in fields.items(): args+=['-F',f'{k}={v}']
    if part is not None: args+=['-F','file=@'+str(part)]
    obj=json.loads(subprocess.check_output(args+[BASE]))
    assert obj['code']==expected,obj
    return obj.get('data',{})
size=2*1073741824
call({'action':'init','name':'too-large.bin','size':size+1},expected=1)
task=call({'action':'init','name':'test-2GiB.bin','size':size})
assert task['count']==10
ident=task['id']; digest=hashlib.sha256()
try:
    with tempfile.TemporaryDirectory() as tmp:
        p=pathlib.Path(tmp)/'part'
        for i in range(task['count']):
            remaining=min(task['chunk_size'],size-i*task['chunk_size'])
            with p.open('wb') as f:
                while remaining:
                    block=bytes([i])*min(1048576,remaining)
                    f.write(block);digest.update(block);remaining-=len(block)
            call({'action':'part','id':ident,'index':i},p)
            print('Part',i+1,'of 10 saved',flush=True)
        p.unlink()
        call({'action':'finish','id':ident})
        actual=hashlib.sha256()
        proc=subprocess.Popen(['curl','-fsS','--max-time','300',BASE+'?id='+ident],stdout=subprocess.PIPE)
        received=0
        for block in iter(lambda:proc.stdout.read(1048576),b''):
            actual.update(block);received+=len(block)
        assert proc.wait()==0 and received==size and actual.digest()==digest.digest()
        print('PASS: exact 2 GiB, adaptive 10 parts, download SHA256, over-limit rejection',flush=True)
finally:
    # Remove only this test's exact random-ID artifacts.
    for ext in ['.bin','.json']:
        pathlib.Path('/var/lib/lanzou-files/'+ident+ext).unlink(missing_ok=True)
    directory=pathlib.Path('/var/lib/lanzou-files/parts-'+ident)
    if directory.exists():
        for p in directory.iterdir():p.unlink()
        directory.rmdir()
