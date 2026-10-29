import hashlib
import io
import zipfile
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase

from scripts.install_backup_tools import download_archive, verified_binary


class BackupToolsTests(SimpleTestCase):
    def setUp(self):
        self.filename = 'rclone-v-test-linux-amd64.zip'
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as package:
            package.writestr('rclone-v-test-linux-amd64/rclone', b'invented executable')
            package.writestr('../unwanted-file', b'must never be extracted')
        self.archive = stream.getvalue()
        self.checksums = hashlib.sha256(self.archive).hexdigest() + '  ' + self.filename

    def test_verified_archive_returns_only_expected_binary(self):
        self.assertEqual(verified_binary(self.archive, self.checksums, self.filename), b'invented executable')

    def test_corrupted_archive_is_rejected_before_extraction(self):
        with self.assertRaises(ValueError):
            verified_binary(self.archive + b'changed', self.checksums, self.filename)

    def test_missing_checksum_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            verified_binary(self.archive, self.checksums, 'another.zip')

    @patch('scripts.install_backup_tools.urlopen')
    def test_403_uses_official_github_fallback(self, download):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = self.archive
        download.side_effect = [HTTPError('https://example.invalid', 403, 'Forbidden', {}, None), response]
        self.assertEqual(download_archive(self.filename), self.archive)
        request = download.call_args_list[1].args[0]
        self.assertTrue(request.full_url.startswith('https://github.com/rclone/rclone/releases/download/'))
        self.assertTrue(request.get_header('User-agent'))

    @patch('scripts.install_backup_tools.urlopen')
    def test_failure_of_both_sources_stops_installation(self, download):
        download.side_effect = HTTPError('https://example.invalid', 403, 'Forbidden', {}, None)
        with self.assertRaises(RuntimeError):
            download_archive(self.filename)
