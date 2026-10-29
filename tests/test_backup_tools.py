import hashlib
import io
import zipfile

from django.test import SimpleTestCase

from scripts.install_backup_tools import verified_binary


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
