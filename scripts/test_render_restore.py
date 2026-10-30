"""Restore a verified backup into an empty, explicitly named test database only."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import uuid

import dj_database_url
import psycopg
from psycopg import sql

# Make the project package importable when executed as a file.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.render_backup import PRIVATE, RCLONE, STATE, database_environment, prepare_config, run_command, write_json


def validate_target(source, target):
    if target.get('ENGINE') != 'django.db.backends.postgresql':
        raise ValueError('Test target must be PostgreSQL.')
    host = str(target.get('HOST', '')).lower().rstrip('.')
    original = str(source.get('HOST', '')).lower().rstrip('.')
    if not host or host.split('.')[0] == original.split('.')[0]:
        raise ValueError('Refusing the original database server, including hostname aliases.')
    if not str(target.get('NAME', '')).startswith('rentalcar_restore_test'):
        raise ValueError('Target database name must begin with rentalcar_restore_test.')


def connect(database):
    return psycopg.connect(host=database['HOST'], port=database.get('PORT') or 5432,
                          dbname=database['NAME'], user=database['USER'],
                          password=database['PASSWORD'], sslmode='require', connect_timeout=30)


def ensure_empty(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')")
        if cursor.fetchone()[0]:
            raise ValueError('Test database is not empty. Nothing will be overwritten.')


def verify_manifest(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest.get('format') != 1 or set(manifest.get('files', {})) != {'database.dump', 'private_uploads.tar.gz'}:
        raise ValueError('Unexpected backup manifest.')
    for name, details in manifest['files'].items():
        path = folder / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != details['bytes']:
            raise ValueError('Missing backup file or size mismatch.')
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != details['sha256']:
            raise ValueError('Backup checksum mismatch.')


def extract_uploads(archive_path, destination):
    count = 0
    with tarfile.open(archive_path, 'r:gz') as archive:
        members = archive.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or '\\' in member.name
                    or not path.parts or path.parts[0] != 'private_uploads'
                    or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe upload archive member; extraction stopped.')
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open('xb') as output:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        output.write(block)
                target.chmod(0o600)
                count += 1
    return count


def main():
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings' or not os.path.ismount('/var/data'):
        raise SystemExit('Run only in Render Shell with the persistent disk.')
    target_url = os.environ.get('RESTORE_TEST_DATABASE_URL', '').strip()
    if not target_url:
        raise SystemExit('Set RESTORE_TEST_DATABASE_URL to the empty test database internal URL.')
    source = dj_database_url.parse(os.environ['DATABASE_URL'])
    target = dj_database_url.parse(target_url)
    validate_target(source, target)
    with connect(target) as connection:
        ensure_empty(connection)
    status = json.loads(STATE.read_text())
    remote = status.get('remote', '')
    if not status.get('last_success') or not re.fullmatch(r'backupcrypt:scheduled/[0-9TZ-]+-[a-f0-9]{8}', remote):
        raise ValueError('No valid successful backup location recorded.')
    work = PRIVATE / ('restore-test-' + uuid.uuid4().hex[:12])
    work.mkdir(mode=0o700, parents=True)
    downloaded = work / 'downloaded'
    restored = work / 'restored'
    downloaded.mkdir(mode=0o700)
    restored.mkdir(mode=0o700)
    print('Downloading and verifying encrypted backup...', flush=True)
    with (work / 'restore.log').open('w') as log:
        run_command([RCLONE, '--config', str(prepare_config()), 'copy', remote, str(downloaded)], log)
        verify_manifest(downloaded)
        restored_files = extract_uploads(downloaded / 'private_uploads.tar.gz', restored)
        # Recheck immediately before restore; no --clean, --create or destructive flags.
        with connect(target) as connection:
            ensure_empty(connection)
        print('Restoring into the separate empty test database...', flush=True)
        run_command(['pg_restore', '--single-transaction', '--exit-on-error', '--no-owner',
                     '--no-privileges', '--dbname', target['NAME'], str(downloaded / 'database.dump')],
                    log, database_environment(target))
    counts = {}
    missing_vouchers = 0
    with connect(target) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        for (table,) in cursor.fetchall():
            cursor.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(table)))
            counts[table] = cursor.fetchone()[0]
        if not counts.get('django_migrations') or not counts.get('auth_user'):
            raise ValueError('Restored application data is incomplete.')
        if 'bookings_bookingvoucher' in counts:
            cursor.execute('SELECT file FROM public.bookings_bookingvoucher')
            root = (restored / 'private_uploads').resolve()
            for (filename,) in cursor.fetchall():
                path = (root / filename).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    missing_vouchers += 1
    report = {'completed_utc': datetime.now(timezone.utc).isoformat(), 'backup': remote,
              'result': 'success' if not missing_vouchers else 'failed',
              'restored_tables': len(counts), 'restored_files': restored_files,
              'missing_vouchers': missing_vouchers, 'table_counts': counts}
    write_json(work / 'report.json', report)
    if missing_vouchers:
        raise ValueError('Restored database references missing voucher files.')
    print(f'RESTORE TEST SUCCESS: {len(counts)} tables; {restored_files} uploaded files; no missing voucher references.', flush=True)
    print('Original database and original uploads were not modified.', flush=True)
    print('Private test report: ' + str(work / 'report.json'), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never print database connection strings or unfiltered provider exceptions.
        if isinstance(error, ValueError):
            print('RESTORE TEST STOPPED: ' + str(error), flush=True)
        else:
            print('RESTORE TEST FAILED (' + type(error).__name__ + '). Check the private restore.log; do not paste secrets.', flush=True)
        raise SystemExit(1)
