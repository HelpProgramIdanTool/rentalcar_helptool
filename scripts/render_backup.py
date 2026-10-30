"""Encrypted Render backups. Run once manually before enabling --loop."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.backup_alerts import notify
from scripts.backup_heartbeat import heartbeat_success
PRIVATE = Path('/var/data/backup-private')
STATE = PRIVATE / 'status.json'
RCLONE = '/var/data/backup-tools/rclone'
POLAND = ZoneInfo('Europe/Warsaw')


def backup_due(now, last_success):
    local = now.astimezone(POLAND)
    if local.hour < 3:
        return False
    if not last_success:
        return True
    return datetime.fromisoformat(last_success).astimezone(POLAND).date() < local.date()


def database_environment(database):
    environment = os.environ.copy()
    environment.update({
        'PGHOST': str(database['HOST']), 'PGPORT': str(database.get('PORT') or 5432),
        'PGUSER': str(database['USER']), 'PGPASSWORD': str(database['PASSWORD']),
        'PGDATABASE': str(database['NAME']), 'PGSSLMODE': 'require',
    })
    return environment


def write_json(path, value):
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.chmod(0o600)
    os.replace(temporary, path)


def prepare_config():
    source = Path('/etc/secrets/rclone.conf')
    if not source.is_file():
        raise RuntimeError('Missing Render secret file rclone.conf.')
    destination = PRIVATE / 'rclone.conf'
    fingerprint = PRIVATE / 'source.sha256'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # Keep refreshed OAuth tokens on the writable disk between runs.
    if not destination.exists() or not fingerprint.exists() or fingerprint.read_text() != digest:
        shutil.copyfile(source, destination)
        destination.chmod(0o600)
        fingerprint.write_text(digest)
        fingerprint.chmod(0o600)
    return destination


def run_command(command, log, environment=None):
    result = subprocess.run(command, env=environment, stdout=log, stderr=log, timeout=1800)
    if result.returncode:
        raise RuntimeError('Backup step failed; see private last-run.log in Render Shell.')


def run_backup():
    import fcntl  # Render/Linux only; no local customer data is uploaded.

    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings' or not os.path.ismount('/var/data'):
        raise RuntimeError('Run only on Render with its persistent disk mounted.')
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
    with (PRIVATE / 'backup.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another backup is already running.') from None
        previous = json.loads(STATE.read_text()) if STATE.exists() else {}
        status = {**previous, 'last_attempt': datetime.now(timezone.utc).isoformat(), 'result': 'running'}
        write_json(STATE, status)
        try:
            sys.path.insert(0, str(ROOT))
            import django
            django.setup()
            from django.conf import settings

            if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
                raise RuntimeError('PostgreSQL is required.')
            media = Path(settings.MEDIA_ROOT)
            if media != Path('/var/data/private_uploads'):
                raise RuntimeError('Unexpected private upload directory.')
            config = prepare_config()
            stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
            remote = 'backupcrypt:scheduled/' + stamp
            log_path = PRIVATE / 'last-run.log'
            log_path.touch(mode=0o600)
            log_path.chmod(0o600)
            with log_path.open('w') as log, tempfile.TemporaryDirectory(prefix='run-', dir=PRIVATE) as work:
                folder = Path(work)
                database = folder / 'database.dump'
                run_command(['pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', str(database)],
                            log, database_environment(settings.DATABASES['default']))
                run_command(['pg_restore', '--list', str(database)], log)
                # Database first, then immutable voucher files referenced by that snapshot.
                # A consistent final migration still requires pausing application writes.
                with tarfile.open(folder / 'private_uploads.tar.gz', 'w:gz') as archive:
                    if media.exists():
                        for child in media.rglob('*'):
                            if child.is_symlink():
                                raise RuntimeError('Symlink in uploads; backup stopped.')
                        archive.add(media, arcname='private_uploads', recursive=True)
                files = {}
                for path in folder.iterdir():
                    digest = hashlib.sha256()
                    with path.open('rb') as handle:
                        for block in iter(lambda: handle.read(1024 * 1024), b''):
                            digest.update(block)
                    files[path.name] = {'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}
                write_json(folder / 'manifest.json', {'format': 1, 'created_utc': stamp, 'files': files})
                prefix = [RCLONE, '--config', str(config)]
                run_command([*prefix, 'copy', str(folder), remote], log)
                # Read back and decrypt all uploaded bytes, comparing to local originals.
                run_command([*prefix, 'check', '--download', '--one-way', str(folder), remote], log)
            status.update(result='success', last_success=datetime.now(timezone.utc).isoformat(), remote=remote)
            write_json(STATE, status)
            heartbeat_success()
            print('BACKUP SUCCESS: database and uploads encrypted; remote read-back verified.', flush=True)
        except Exception:
            status['result'] = 'failed'
            write_json(STATE, status)
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loop', action='store_true')
    args = parser.parse_args()
    if not args.loop:
        try:
            run_backup()
        except Exception as error:
            notify('failure')
            print(f'BACKUP FAILED ({type(error).__name__}). No success recorded; check private diagnostics.', flush=True)
            raise SystemExit(1)
        notify('recovery')
        return
    print('Backup scheduler: daily at 03:00 Europe/Warsaw; automatic deletion disabled.', flush=True)
    while True:
        status = json.loads(STATE.read_text()) if STATE.exists() else {}
        if backup_due(datetime.now(timezone.utc), status.get('last_success')):
            try:
                run_backup()
            except Exception as error:
                notify('failure')
                print(f'BACKUP FAILED ({type(error).__name__}); retry in one hour.', flush=True)
                time.sleep(3600)
            else:
                notify('recovery')
        time.sleep(60)


if __name__ == '__main__':
    main()
