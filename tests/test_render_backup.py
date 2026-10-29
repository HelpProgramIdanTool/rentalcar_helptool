from datetime import datetime, timezone
import os
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.render_backup import backup_due, database_environment


class RenderBackupTests(SimpleTestCase):
    def test_first_backup_waits_until_three_in_poland(self):
        self.assertFalse(backup_due(datetime(2026, 10, 29, 1, 59, tzinfo=timezone.utc), None))
        self.assertTrue(backup_due(datetime(2026, 10, 29, 2, 0, tzinfo=timezone.utc), None))

    def test_success_prevents_repeating_on_same_local_date(self):
        now = datetime(2026, 10, 29, 20, 0, tzinfo=timezone.utc)
        self.assertFalse(backup_due(now, '2026-10-29T02:00:00+00:00'))
        self.assertTrue(backup_due(now, '2026-10-28T02:00:00+00:00'))

    def test_summer_time_uses_polish_three_am(self):
        self.assertFalse(backup_due(datetime(2026, 7, 1, 0, 59, tzinfo=timezone.utc), None))
        self.assertTrue(backup_due(datetime(2026, 7, 1, 1, 0, tzinfo=timezone.utc), None))

    def test_database_values_go_into_process_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            result = database_environment({'HOST': 'test-host', 'PORT': '', 'USER': 'test-user',
                                           'PASSWORD': 'fake-password', 'NAME': 'test-db'})
        self.assertEqual(result['PGPASSWORD'], 'fake-password')
        self.assertEqual(result['PGDATABASE'], 'test-db')
        self.assertEqual(result['PGPORT'], '5432')
        self.assertEqual(result['PGSSLMODE'], 'require')
