from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.backup_alerts import build_message, notify, should_notify


class BackupAlertTests(SimpleTestCase):
    def test_first_failure_sends_and_repeats_are_limited_to_six_hours(self):
        now = datetime(2026, 10, 30, 2, tzinfo=timezone.utc)
        self.assertTrue(should_notify('failure', {}, now))
        state = {'last_failure_sent': now.isoformat()}
        self.assertFalse(should_notify('failure', state, now + timedelta(hours=1)))
        self.assertTrue(should_notify('failure', state, now + timedelta(hours=6)))

    def test_normal_success_does_not_send_recovery_but_previous_outage_does(self):
        now = datetime.now(timezone.utc)
        self.assertFalse(should_notify('recovery', {}, now))
        self.assertTrue(should_notify('recovery', {'outage_notified': True}, now))

    def test_message_contains_recipient_and_polish_time_without_password(self):
        config = {'sender': 'sender@example.com', 'recipient': 'operator@example.com', 'password': 'FAKE-SECRET'}
        message = build_message(config, 'failure', datetime(2026, 10, 30, 2, tzinfo=timezone.utc))
        self.assertEqual(message['To'], 'operator@example.com')
        self.assertIn('30.10.2026 03:00', message.get_content())
        self.assertNotIn('FAKE-SECRET', message.as_string())

    @patch('scripts.backup_alerts.smtplib.SMTP')
    def test_failed_delivery_does_not_record_sent_or_hide_error(self, smtp):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            config = folder / 'config.json'
            config.write_text(json.dumps({'sender': 'sender@example.com', 'recipient': 'test@example.com', 'password': 'fake'}))
            state = folder / 'state.json'
            smtp.side_effect = OSError('fake connection failure')
            with patch('scripts.backup_alerts.CONFIG', config), patch('scripts.backup_alerts.STATE', state), patch('scripts.backup_alerts.BACKUP_STATUS', folder / 'missing.json'):
                self.assertFalse(notify('failure'))
            self.assertFalse(state.exists())

    @patch('scripts.backup_alerts.smtplib.SMTP')
    def test_failure_then_recovery_sends_only_expected_messages(self, smtp):
        smtp.return_value.__enter__.return_value.send_message.return_value = {}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            config = folder / 'config.json'
            config.write_text(json.dumps({'sender': 'sender@example.com', 'recipient': 'test@example.com', 'password': 'fake'}))
            state = folder / 'state.json'
            with patch('scripts.backup_alerts.CONFIG', config), patch('scripts.backup_alerts.STATE', state), patch('scripts.backup_alerts.BACKUP_STATUS', folder / 'missing.json'):
                self.assertTrue(notify('failure'))
                self.assertTrue(notify('failure'))
                self.assertTrue(notify('recovery'))
                self.assertTrue(notify('recovery'))
                self.assertFalse(json.loads(state.read_text())['outage_notified'])
            self.assertEqual(smtp.call_count, 2)
