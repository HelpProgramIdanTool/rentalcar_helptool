import os
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts.backup_heartbeat import heartbeat_success


class BackupHeartbeatTests(SimpleTestCase):
    url = 'https://hc-ping.com/00000000-0000-4000-8000-000000000000'

    @patch('scripts.backup_heartbeat.build_opener')
    def test_not_configured_makes_no_request(self, opener):
        with patch.dict(os.environ, {'BACKUP_HEARTBEAT_URL': ''}):
            self.assertFalse(heartbeat_success())
        opener.assert_not_called()

    @patch('scripts.backup_heartbeat.build_opener')
    def test_rejects_other_hosts_query_strings_and_plain_http(self, opener):
        for url in ('http://hc-ping.com/test', 'https://example.com/test', self.url + '?secret=test'):
            with self.subTest(url=url), patch.dict(os.environ, {'BACKUP_HEARTBEAT_URL': url}):
                self.assertFalse(heartbeat_success())
        opener.assert_not_called()

    @patch('scripts.backup_heartbeat.build_opener')
    def test_sends_empty_success_signal_without_logs_or_credentials(self, opener):
        opener.return_value.open.return_value.__enter__.return_value.status = 200
        with patch.dict(os.environ, {'BACKUP_HEARTBEAT_URL': self.url}):
            self.assertTrue(heartbeat_success())
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.data, b'')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.full_url, self.url)

    @patch('scripts.backup_heartbeat.time.sleep')
    @patch('scripts.backup_heartbeat.build_opener')
    def test_network_failure_retries_without_raising(self, opener, sleep):
        opener.return_value.open.side_effect = OSError('unavailable')
        with patch.dict(os.environ, {'BACKUP_HEARTBEAT_URL': self.url}):
            self.assertFalse(heartbeat_success())
        self.assertEqual(opener.return_value.open.call_count, 3)
