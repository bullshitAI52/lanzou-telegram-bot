import pathlib, secrets, os, shutil, time
root = pathlib.Path('/var/www/lanzou')
backup = pathlib.Path('/root/lanzou-backup-' + str(int(time.time())))
backup.mkdir(mode=0o700)
for src in ['/etc/nginx/sites-available/lanzou-8089.conf', '/opt/lanzou-telegram-bot/bot.py']:
    shutil.copy2(src, backup / pathlib.Path(src).name)
store = pathlib.Path('/var/lib/lanzou-files')
store.mkdir(exist_ok=True, mode=0o750)
shutil.chown(store, user='www-data', group='www-data')
key = pathlib.Path('/etc/lanzou-upload.key')
if not key.exists():
    key.write_text(secrets.token_urlsafe(24))
key.chmod(0o640)
shutil.chown(key, user='root', group='www-data')
env = pathlib.Path('/etc/lanzou-telegram.env')
lines = [line for line in env.read_text().splitlines() if not line.startswith('LOCAL_UPLOAD_KEY=')]
env.write_text('\n'.join(lines) + '\nLOCAL_UPLOAD_KEY=' + key.read_text().strip() + '\n')
env.chmod(0o600)
for name in ['local-store.php', 'local.html']:
    shutil.copy2('/tmp/lanzou-local-deploy/' + name, root / name)
shutil.copy2('/tmp/lanzou-local-deploy/lanzou-bot.py', '/opt/lanzou-telegram-bot/bot.py')
shutil.copy2('/tmp/lanzou-local-deploy/lanzou-8089.conf', '/etc/nginx/sites-available/lanzou-8089.conf')
pathlib.Path('/etc/cron.d/lanzou-files-cleanup').write_text('*/10 * * * * www-data /usr/bin/php /var/www/lanzou/local-store.php >/dev/null 2>&1\n')
print('Deployment files installed; backup:', backup)
