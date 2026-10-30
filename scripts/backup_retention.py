"""Conservative retention for verified backup directories, never other Drive data."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

POLAND = ZoneInfo('Europe/Warsaw')
PREFIX = 'backupcrypt:scheduled/'
FILES = {'database.dump', 'private_uploads.tar.gz', 'manifest.json', 'verified.json'}


def stamp_for(name):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{6}Z-[a-f0-9]{8}', name):
        return None
    try:
        return datetime.strptime(name[:18], '%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def retention_plan(records, now, latest_success):
    names = [item['name'] for item in records]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate backup names; refusing retention.')
    valid = {item['name']: stamp_for(item['name']) for item in records
             if item.get('verified') and stamp_for(item['name']) is not None}
    if latest_success not in valid:
        raise ValueError('Latest successful backup is not verified; nothing may be removed.')
    today = now.astimezone(POLAND).date()
    cutoff = today - timedelta(days=29)
    current_month = today.year * 12 + today.month
    keep = {latest_success}
    monthly = {}
    for name, stamp in valid.items():
        local = stamp.astimezone(POLAND)
        if local.date() >= cutoff:
            keep.add(name)
        month = local.year * 12 + local.month
        if 0 <= current_month - month < 12:
            previous = monthly.get(month)
            if previous is None or (stamp, name) > (valid[previous], previous):
                monthly[month] = name
    keep.update(monthly.values())
    delete = set(valid) - keep
    # Unrecognized and unverified directories are always left untouched.
    return {'keep': sorted(set(names) - delete), 'delete': sorted(delete)}


def prune_backups(apply=False):
    from scripts.render_backup import PRIVATE, RCLONE, STATE, prepare_config
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings' or not os.path.ismount('/var/data'):
        raise RuntimeError('Run only on Render with its persistent disk.')
    status = json.loads(STATE.read_text())
    now = datetime.now(timezone.utc)
    success = datetime.fromisoformat(status['last_success'])
    if status.get('result') != 'success' or not timedelta(0) <= now - success < timedelta(hours=24):
        raise RuntimeError('A fresh verified backup is required before retention.')
    remote = status['remote']
    if not remote.startswith(PREFIX) or stamp_for(remote[len(PREFIX):]) is None:
        raise RuntimeError('Unexpected backup root.')
    latest = remote[len(PREFIX):]
    prefix = [RCLONE, '--config', str(prepare_config())]

    def command(*args):
        result = subprocess.run([*prefix, *args], capture_output=True, text=True, timeout=180)
        if result.returncode:
            # Provider errors may contain paths or private endpoint details.
            (PRIVATE / 'retention-error.log').write_text(result.stderr, encoding='utf-8')
            (PRIVATE / 'retention-error.log').chmod(0o600)
            raise RuntimeError('Retention command failed. Private diagnostic log saved.')
        return result.stdout

    records = []
    listing = json.loads(command('lsjson', PREFIX, '--dirs-only'))
    for item in listing:
        name = item['Path']
        verified = False
        if stamp_for(name) is not None:
            entries = json.loads(command('lsjson', PREFIX + name, '--files-only'))
            if {entry['Path'] for entry in entries} == FILES and len(entries) == len(FILES):
                marker = json.loads(command('cat', PREFIX + name + '/verified.json'))
                verified = marker.get('format') == 1 and marker.get('backup') == name
        records.append({'name': name, 'verified': verified})
    plan = retention_plan(records, now, latest)
    write_report = {'mode': 'apply' if apply else 'plan', 'created_utc': now.isoformat(), **plan}
    from scripts.render_backup import write_json
    write_json(PRIVATE / 'retention-report.json', write_report)
    print(f"RETENTION {'APPLY' if apply else 'PLAN'}: keep {len(plan['keep'])}; remove {len(plan['delete'])}.", flush=True)
    if not apply:
        print('No files removed.', flush=True)
        return
    for name in plan['delete']:
        if stamp_for(name) is None or name == latest:
            raise RuntimeError('Unsafe retention candidate.')
        # Recheck immediately before deleting only the four known files.
        entries = json.loads(command('lsjson', PREFIX + name))
        if len(entries) != 4 or {entry['Path'] for entry in entries} != FILES or any(entry.get('IsDir') for entry in entries):
            raise RuntimeError('Backup directory changed; deletion stopped.')
        # Removing the marker first ensures an interrupted prune is never a verified backup.
        for filename in ('verified.json', 'database.dump', 'private_uploads.tar.gz', 'manifest.json'):
            command('deletefile', PREFIX + name + '/' + filename)
        command('rmdir', PREFIX + name)
    print('RETENTION COMPLETE. Latest verified backup preserved.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    arguments = parser.parse_args()
    try:
        prune_backups(apply=arguments.apply)
    except Exception as error:
        print('RETENTION STOPPED (' + type(error).__name__ + '). No further removals attempted.', flush=True)
        raise SystemExit(1)
