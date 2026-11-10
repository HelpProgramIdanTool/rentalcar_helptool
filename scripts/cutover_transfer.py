"""Private, verified data transfer; rehearsal never writes to the live database."""
import argparse
from collections import Counter
from contextlib import contextmanager, closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import sys
import subprocess
import tempfile
import uuid
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def safe_name(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Unsafe archive member name')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or ':' in value:
        raise ValueError('Unsafe archive member path')
    return path


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_record(record):
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def serialize_record(obj):
    """Keep full time precision; Django's JSON encoder drops microseconds."""
    from django.core import serializers
    from django.db.models import DateTimeField, TimeField
    record = json.loads(serializers.serialize('json', [obj]))[0]
    for field in obj._meta.fields:
        if isinstance(field, (DateTimeField, TimeField)) and field.name in record['fields']:
            value = getattr(obj, field.attname)
            if value is not None:
                encoded = value.isoformat()
                record['fields'][field.name] = encoded[:-6] + 'Z' if encoded.endswith('+00:00') else encoded
    return record


def model_inventory(alias):
    from django.apps import apps
    from django.core import serializers
    result = {}
    for model in sorted(apps.get_models(), key=lambda m: m._meta.label_lower):
        if model._meta.label_lower == 'sessions.session':
            continue  # Browser sessions are intentionally not moved across servers.
        digest = hashlib.sha256()
        count = 0
        for obj in model._base_manager.using(alias).order_by('pk').iterator():
            record = serialize_record(obj)
            digest.update((canonical_record(record) + '\n').encode())
            count += 1
        result[model._meta.label_lower] = {'count': count, 'sha256': digest.hexdigest()}
    return result


@contextmanager
def database_alias(alias, configuration):
    from django.db import connections
    if alias in connections.databases:
        raise ValueError('Temporary database alias already exists')
    connections.databases[alias] = deepcopy(configuration)
    try:
        yield alias
    finally:
        connections[alias].close()
        del connections[alias]
        del connections.databases[alias]


def export_bundle(destination):
    from django.apps import apps
    from django.conf import settings
    from django.core import serializers
    from django.db import connections
    from django.db.models import FileField
    from config.version import APP_VERSION
    target = Path(destination).resolve()
    if target.exists():
        raise ValueError('Refusing to overwrite an existing transfer package')
    if connections['default'].vendor != 'sqlite':
        raise ValueError('Export must run against the authoritative local SQLite database')
    target.parent.mkdir(parents=True, exist_ok=True)
    configuration = deepcopy(connections.databases['default'])
    alias = 'cutover_source_' + uuid.uuid4().hex
    staging = target.with_suffix('.partial')
    try:
        with tempfile.TemporaryDirectory(prefix='cutover-', dir=target.parent) as work:
            work = Path(work)
            snapshot = work / 'source.sqlite3'
            with closing(sqlite3.connect(configuration['NAME'])) as source, closing(sqlite3.connect(snapshot)) as copied:
                source.backup(copied)
                if copied.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Source SQLite snapshot integrity check failed')
            configuration['NAME'] = str(snapshot)
            files = {}
            counts = Counter()
            manifest = {'format': 1, 'app_version': APP_VERSION,
                        'excluded_models': ['sessions.session'], 'files': {}}
            with database_alias(alias, configuration):
                fixture = work / 'records.jsonl'
                with fixture.open('w', encoding='utf8', newline='\n') as output:
                    for model in sorted(apps.get_models(), key=lambda m: m._meta.label_lower):
                        label = model._meta.label_lower
                        if label == 'sessions.session':
                            continue
                        counts[label] = 0
                        fields = [f for f in model._meta.fields if isinstance(f, FileField)]
                        for obj in model._base_manager.using(alias).order_by('pk').iterator():
                            record = serialize_record(obj)
                            output.write(canonical_record(record) + '\n')
                            counts[label] += 1
                            for field in fields:
                                value = getattr(obj, field.name)
                                if not value:
                                    continue
                                name = str(safe_name(value.name))
                                path = Path(value.path).resolve()
                                if not path.is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
                                    raise ValueError('Attachment outside private media directory')
                                if not path.is_file():
                                    raise ValueError('Referenced attachment is missing; export stopped')
                                if name in files and files[name] != path:
                                    raise ValueError('Conflicting attachment names')
                                files[name] = path
                manifest['models'] = model_inventory(alias)
                assert {k: v['count'] for k, v in manifest['models'].items()} == dict(counts)
            manifest['records_sha256'] = digest_file(fixture)
            with ZipFile(staging, 'x', compression=ZIP_DEFLATED, compresslevel=6) as archive:
                archive.write(fixture, 'records.jsonl')
                for name, path in sorted(files.items()):
                    archive.write(path, 'media/' + name)
                    manifest['files'][name] = {'bytes': path.stat().st_size, 'sha256': digest_file(path)}
                archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=True, indent=2))
            staging.replace(target)
        target.chmod(0o600)
        return {'package': str(target), 'bytes': target.stat().st_size,
                'sha256': digest_file(target), 'models': len(manifest['models']),
                'records': sum(counts.values()), 'attachments': len(files)}
    finally:
        if staging.exists():
            staging.unlink()


def unpack_bundle(package, destination):
    destination = Path(destination).resolve()
    with ZipFile(package) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or sum(i.file_size for i in infos) > 2 * 1024**3:
            raise ValueError('Duplicate members or oversized transfer package')
        for name in names:
            safe_name(name)
        if not {'manifest.json', 'records.jsonl'} <= set(names):
            raise ValueError('Incomplete transfer package')
        if archive.getinfo('manifest.json').file_size > 4 * 1024**2:
            raise ValueError('Oversized manifest')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 1:
            raise ValueError('Unsupported transfer format')
        expected = {'manifest.json', 'records.jsonl'} | {'media/' + str(safe_name(n)) for n in manifest['files']}
        if set(names) != expected:
            raise ValueError('Archive does not match manifest')
        for info in infos:
            target = destination.joinpath(*safe_name(info.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
    if digest_file(destination / 'records.jsonl') != manifest['records_sha256']:
        raise ValueError('Database fixture checksum mismatch')
    for name, evidence in manifest['files'].items():
        path = destination / 'media' / name
        if path.stat().st_size != evidence['bytes'] or digest_file(path) != evidence['sha256']:
            raise ValueError('Attachment checksum mismatch')
    return manifest


def load_into_new_database(alias, folder, manifest):
    from django.apps import apps
    from django.core.management import call_command
    from django.core.management.color import no_style
    from django.db import connections, transaction
    from django.conf import settings
    connection = connections[alias]
    if alias != 'default' or not getattr(settings, 'CUTOVER_ISOLATED_WORKER', False):
        raise ValueError('Refusing non-rehearsal database alias')
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_schema()')
            if not re.fullmatch(r'cutover_trial_[a-f0-9]{32}', cursor.fetchone()[0] or ''):
                raise ValueError('Refusing non-trial schema')
    if connection.introspection.table_names():
        raise ValueError('Rehearsal database/schema must be empty')
    call_command('migrate', database=alias, interactive=False, verbosity=0)
    # The caller must create a brand-new isolated target. Seed rows produced by
    # migrations are removed only inside that explicitly isolated database/schema.
    with connection.constraint_checks_disabled(), transaction.atomic(using=alias):
        tables = [t for t in connection.introspection.table_names() if t != 'django_migrations']
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute('SELECT current_schema()')
                if not re.fullmatch(r'cutover_trial_[a-f0-9]{32}', cursor.fetchone()[0] or ''):
                    raise ValueError('Refusing non-trial schema')
                cursor.execute('TRUNCATE ' + ', '.join(connection.ops.quote_name(t) for t in tables) + ' RESTART IDENTITY CASCADE')
            else:
                for table in tables:
                    cursor.execute('DELETE FROM ' + connection.ops.quote_name(table))
        call_command('loaddata', str(Path(folder) / 'records.jsonl'), database=alias, verbosity=0)
        connection.check_constraints()
        with connection.cursor() as cursor:
            for statement in connection.ops.sequence_reset_sql(no_style(), apps.get_models()):
                cursor.execute(statement)
        inventory = model_inventory(alias)
        if inventory != manifest['models']:
            different = [m for m in set(inventory) | set(manifest['models']) if inventory.get(m) != manifest['models'].get(m)]
            from django.core import serializers
            samples = []
            for line in (Path(folder) / 'records.jsonl').open(encoding='utf8'):
                record = json.loads(line)
                if record['model'] not in different or any(s['model']==record['model'] for s in samples):
                    continue
                model = apps.get_model(record['model'])
                obj = model._base_manager.using(alias).filter(pk=record['pk']).first()
                restored = serialize_record(obj) if obj else None
                if restored != record:
                    samples.append({'model':record['model'],'pk':record['pk'], 'differences':{
                        key:{'source':value,'restored':restored['fields'].get(key) if restored else None}
                        for key,value in record['fields'].items() if not restored or value!=restored['fields'].get(key)}})
            (Path(folder) / 'verification-differences.json').write_text(json.dumps({'models':different,'samples':samples,
                'counts':{m:{'source':manifest['models'].get(m),'restored':inventory.get(m)} for m in different}},ensure_ascii=True,indent=2),encoding='utf8')
            raise ValueError('Restored model verification failed: ' + ', '.join(sorted(different)))
    return inventory


def isolated_restore(configuration, folder, verify_only=False):
    import os
    environment = os.environ.copy()
    environment['CUTOVER_ISOLATED_DATABASE'] = json.dumps(configuration)
    environment['CUTOVER_ISOLATED_DIRECTORY'] = str(Path(folder).resolve())
    environment['DJANGO_SETTINGS_MODULE'] = 'config.cutover_settings'
    print('Restoring isolated copy and verifying every record; this may take several minutes...', flush=True)
    with (Path(folder) / 'restore-worker.log').open('wb') as log:
        operation = '_verify-worker' if verify_only else '_restore-worker'
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), operation, str(Path(folder).resolve())],
                                   env=environment, stdout=log, stderr=subprocess.STDOUT)
        try:
            for minute in range(30):
                try:
                    result = process.wait(timeout=60)
                    break
                except subprocess.TimeoutExpired:
                    print(f'Restore still running: {minute + 1} minute(s).', flush=True)
            else:
                raise TimeoutError('Restore exceeded 30 minutes')
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise
    if result:
        raise RuntimeError('Isolated restore failed; see the private restore-worker.log')


def local_rehearsal(package, destination):
    from django.db import connections
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Rehearsal destination must not exist')
    destination.mkdir(parents=True)
    manifest = unpack_bundle(package, destination)
    configuration = deepcopy(connections.databases['default'])
    configuration.update(ENGINE='django.db.backends.sqlite3', NAME=str(destination / 'restored.sqlite3'), OPTIONS={})
    isolated_restore(configuration, destination)
    return {'result': 'verified', 'models': len(manifest['models']),
            'records': sum(v['count'] for v in manifest['models'].values()), 'attachments': len(manifest['files'])}


def postgres_rehearsal(package):
    import os
    import dj_database_url
    import psycopg
    from psycopg import sql
    from django.conf import settings
    from scripts.test_render_restore import validate_target, connect
    target = {**deepcopy(settings.DATABASES['default']),
              **dj_database_url.parse(os.environ.get('RESTORE_TEST_DATABASE_URL', ''))}
    validate_target(settings.DATABASES['default'], target)
    schema = 'cutover_trial_' + uuid.uuid4().hex
    # Existing public-schema restoration test data remains untouched.
    with connect(target) as control:
        control.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    target.setdefault('OPTIONS', {})['options'] = '-c search_path=' + schema
    private = Path('/var/data/backup-private') / schema
    private.mkdir(parents=True, exist_ok=False)
    manifest = unpack_bundle(package, private)
    isolated_restore(target, private)
    report = {'result': 'verified', 'schema': schema, 'models': len(manifest['models']),
              'records': sum(v['count'] for v in manifest['models'].values()), 'attachments': len(manifest['files'])}
    (private / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    return report


def require_empty_primary(connection):
    """This first cutover must never replace orders already entered online."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM public.bookings_booking')
        if cursor.fetchone()[0]:
            raise ValueError('Server already contains bookings; cutover stopped')


def stage_primary(package, expected_sha256):
    """Prepare a verified new schema on Render; do not switch the live app."""
    import os
    from psycopg import sql
    from django.conf import settings
    from scripts.test_render_restore import connect
    from scripts.render_backup import database_environment
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings' or not os.path.ismount('/var/data'):
        raise ValueError('Run staging only in Render Shell with its persistent disk')
    if not re.fullmatch('[a-f0-9]{64}', expected_sha256) or digest_file(package) != expected_sha256:
        raise ValueError('Final package checksum does not match')
    target = deepcopy(settings.DATABASES['default'])
    if target['ENGINE'] != 'django.db.backends.postgresql':
        raise ValueError('Render PostgreSQL required')
    schema = 'cutover_trial_' + uuid.uuid4().hex
    private = Path('/var/data/backup-private') / schema
    private.mkdir(parents=True, exist_ok=False, mode=0o700)
    manifest = unpack_bundle(package, private)
    with connect(target) as control:
        require_empty_primary(control)
    print('Saving current server database before staging...', flush=True)
    backup = private / 'server-before-staging.dump'
    with (private / 'pg-dump.log').open('wb') as log:
        subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', str(backup)],
                       env=database_environment(target), stdout=log, stderr=log, check=True, timeout=600)
    backup.chmod(0o600)
    with connect(target) as control:
        require_empty_primary(control)
        control.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    target.setdefault('OPTIONS', {})['options'] = '-c search_path=' + schema
    isolated_restore(target, private)
    report = {'result': 'staged-not-live', 'schema': schema, 'package_sha256': expected_sha256,
              'server_backup_sha256': digest_file(backup), 'models': len(manifest['models']),
              'records': sum(v['count'] for v in manifest['models'].values()), 'attachments': len(manifest['files'])}
    (private / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    return report


def install_verified_media(folder, media_root, manifest):
    """Copy only declared attachments; conflicting existing files are preserved."""
    root = Path(media_root).resolve()
    for name, evidence in manifest['files'].items():
        safe_name(name)
        source = Path(folder) / 'media' / name
        destination = (root / name).resolve()
        if not destination.is_relative_to(root):
            raise ValueError('Attachment escapes media directory')
        if source.stat().st_size != evidence['bytes'] or digest_file(source) != evidence['sha256']:
            raise ValueError('Staged attachment checksum mismatch')
        if destination.exists() and digest_file(destination) != evidence['sha256']:
            raise ValueError('Existing attachment conflicts; nothing will be overwritten')
    for name in manifest['files']:
        destination = root / name
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with (Path(folder) / 'media' / name).open('rb') as source, destination.open('xb') as output:
            shutil.copyfileobj(source, output)
        destination.chmod(0o600)
        if digest_file(destination) != manifest['files'][name]['sha256']:
            raise ValueError('Installed attachment verification failed')


def activate_primary(schema, expected_sha256):
    """Switch only a verified first-cutover schema; retain the old public schema."""
    import os
    from psycopg import sql
    from django.conf import settings
    from scripts.test_render_restore import connect
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings' or not os.path.ismount('/var/data'):
        raise ValueError('Activate only in Render Shell with its persistent disk')
    if not re.fullmatch(r'cutover_trial_[a-f0-9]{32}', schema):
        raise ValueError('Invalid staged schema')
    private = Path('/var/data/backup-private') / schema
    report = json.loads((private / 'report.json').read_text(encoding='utf8'))
    if report.get('result') != 'staged-not-live' or report.get('schema') != schema or report.get('package_sha256') != expected_sha256:
        raise ValueError('A matching verified primary staging report is required')
    if digest_file(private / 'server-before-staging.dump') != report['server_backup_sha256']:
        raise ValueError('Original server backup checksum mismatch')
    manifest = json.loads((private / 'manifest.json').read_text(encoding='utf8'))
    if digest_file(private / 'records.jsonl') != manifest['records_sha256']:
        raise ValueError('Staged fixture checksum mismatch')
    target = deepcopy(settings.DATABASES['default'])
    target.setdefault('OPTIONS', {})['options'] = '-c search_path=' + schema
    isolated_restore(target, private, verify_only=True)
    install_verified_media(private, settings.MEDIA_ROOT, manifest)
    previous = 'cutover_previous_' + uuid.uuid4().hex
    # Both renames commit together. Existing database objects are retained by OID.
    with connect(settings.DATABASES['default']) as control:
        control.execute("SET LOCAL lock_timeout = '15s'")
        control.execute('LOCK TABLE public.bookings_booking IN ACCESS EXCLUSIVE MODE')
        require_empty_primary(control)
        control.execute(sql.SQL('ALTER SCHEMA public RENAME TO {}').format(sql.Identifier(previous)))
        control.execute(sql.SQL('ALTER SCHEMA {} RENAME TO public').format(sql.Identifier(schema)))
    report.update(result='activated-restart-required', previous_schema=previous)
    (private / 'activation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    return report


def main():
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    if len(sys.argv) == 3 and sys.argv[1] in ('_restore-worker', '_verify-worker'):
        from django.conf import settings
        if not getattr(settings, 'CUTOVER_ISOLATED_WORKER', False):
            raise ValueError('Isolated settings required')
        folder = Path(sys.argv[2]).resolve()
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf8'))
        if digest_file(folder / 'records.jsonl') != manifest['records_sha256']:
            raise ValueError('Fixture changed before restore')
        if sys.argv[1] == '_restore-worker':
            load_into_new_database('default', folder, manifest)
        elif model_inventory('default') != manifest['models']:
            raise ValueError('Staged database verification failed before activation')
        print('ISOLATED RESTORE VERIFIED')
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    export = sub.add_parser('export'); export.add_argument('destination')
    local = sub.add_parser('local-test'); local.add_argument('package'); local.add_argument('destination')
    trial = sub.add_parser('postgres-test'); trial.add_argument('package')
    stage = sub.add_parser('stage-primary'); stage.add_argument('package'); stage.add_argument('--sha256', required=True)
    activate = sub.add_parser('activate-primary'); activate.add_argument('schema'); activate.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if args.operation == 'export': result = export_bundle(args.destination)
    elif args.operation == 'local-test': result = local_rehearsal(args.package, args.destination)
    elif args.operation == 'postgres-test': result = postgres_rehearsal(args.package)
    elif args.operation == 'stage-primary': result = stage_primary(args.package, args.sha256)
    else: result = activate_primary(args.schema, args.sha256)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
