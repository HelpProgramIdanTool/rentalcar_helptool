from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.backup_retention import FILES, PREFIX, prune_backups, retention_plan, stamp_for


def record(day, suffix='00000000', verified=True):
    return {'name': day + 'T020000Z-' + suffix, 'verified': verified}


class BackupRetentionTests(SimpleTestCase):
    now = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)

    def plan(self, records):
        return retention_plan(records, self.now, records[-1]['name'])

    def test_keeps_all_runs_in_last_thirty_polish_dates(self):
        rows = [record('2026-10-01'), record('2026-10-01', '11111111'), record('2026-10-30')]
        self.assertEqual(self.plan(rows)['delete'], [])

    def test_keeps_last_verified_run_per_month_and_prunes_other_old_runs(self):
        rows = [record('2026-09-01'), record('2026-09-30'), record('2026-10-30')]
        self.assertEqual(self.plan(rows)['delete'], [rows[0]['name']])
        self.assertIn(rows[1]['name'], self.plan(rows)['keep'])

    def test_year_boundary_and_twelve_calendar_month_window(self):
        rows = [record('2025-10-31'), record('2025-11-30'), record('2026-01-31'), record('2026-10-30')]
        self.assertEqual(self.plan(rows)['delete'], [rows[0]['name']])

    def test_unknown_and_unverified_directories_are_never_removed(self):
        rows = [record('2020-01-01', verified=False), {'name': '../other-folder', 'verified': True}, record('2026-10-30')]
        self.assertEqual(self.plan(rows)['delete'], [])
        self.assertIsNone(stamp_for('../other-folder'))

    def test_latest_success_is_preserved_even_if_old(self):
        rows = [record('2020-01-01')]
        self.assertEqual(self.plan(rows)['delete'], [])

    def test_missing_or_unverified_latest_refuses_the_whole_plan(self):
        rows = [record('2026-10-30', verified=False)]
        with self.assertRaises(ValueError):
            self.plan(rows)
        with self.assertRaises(ValueError):
            retention_plan([], self.now, 'missing')

    def test_duplicate_names_refuse_plan(self):
        row = record('2026-10-30')
        with self.assertRaises(ValueError):
            self.plan([row, row])

    def test_monthly_selection_uses_polish_month_not_utc_month(self):
        rows = [record('2026-08-31'), {'name': '2026-08-31T230000Z-11111111', 'verified': True}, record('2026-09-30'), record('2026-10-30')]
        plan = self.plan(rows)
        self.assertIn(rows[0]['name'], plan['keep'])
        self.assertIn(rows[1]['name'], plan['delete'])

    def test_dry_run_never_deletes_and_apply_only_targets_expired_known_files(self):
        now = datetime.now(timezone.utc)
        latest = now.strftime('%Y-%m-%dT%H%M%SZ') + '-11111111'
        old = '2020-01-01T020000Z-00000000'
        for apply in (False, True):
            with self.subTest(apply=apply), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                state = folder / 'status.json'
                state.write_text(json.dumps({'result': 'success', 'last_success': now.isoformat(), 'remote': PREFIX + latest}))
                calls = []

                def fake_run(command, **kwargs):
                    arguments = command[3:]
                    calls.append(arguments)
                    if arguments == ['lsjson', PREFIX, '--dirs-only']:
                        value = [{'Path': old}, {'Path': latest}]
                    elif arguments[0] == 'lsjson':
                        value = [{'Path': name, 'IsDir': False} for name in FILES]
                    elif arguments[0] == 'cat':
                        value = {'format': 1, 'backup': arguments[1].split('/')[-2]}
                    else:
                        self.assertIn(arguments[0], ('deletefile', 'rmdir'))
                        self.assertTrue(arguments[1] == PREFIX + old or arguments[1] in {PREFIX + old + '/' + name for name in FILES})
                        value = None
                    return SimpleNamespace(returncode=0, stdout=json.dumps(value), stderr='')

                with patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'config.render_settings'}), patch('scripts.backup_retention.os.path.ismount', return_value=True), patch('scripts.render_backup.PRIVATE', folder), patch('scripts.render_backup.STATE', state), patch('scripts.render_backup.prepare_config', return_value=folder / 'config'), patch('scripts.backup_retention.subprocess.run', side_effect=fake_run):
                    prune_backups(apply=apply)
                deletes = [call for call in calls if call[0] == 'deletefile']
                self.assertEqual(len(deletes), 4 if apply else 0)
                self.assertTrue(all(latest not in call[1] for call in deletes))
