import hashlib
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile

from django.test import SimpleTestCase
from scripts.cutover_transfer import safe_name, unpack_bundle, local_rehearsal, canonical_record


class CutoverPackageTests(SimpleTestCase):
    def test_restore_reports_progress_until_worker_finishes(self):
        from unittest.mock import patch, MagicMock
        import subprocess
        from scripts.cutover_transfer import isolated_restore
        worker = MagicMock()
        worker.wait.side_effect = [subprocess.TimeoutExpired('test', 60), 0]
        with tempfile.TemporaryDirectory() as work, patch('scripts.cutover_transfer.subprocess.Popen', return_value=worker), patch('builtins.print') as output:
            isolated_restore({}, work)
            self.assertTrue(any('1 minute(s)' in str(call) for call in output.call_args_list))
            worker.terminate.assert_not_called()

    def test_interruption_stops_restore_worker(self):
        from unittest.mock import patch, MagicMock
        from scripts.cutover_transfer import isolated_restore
        worker = MagicMock()
        worker.wait.side_effect = [KeyboardInterrupt(), 0]
        with tempfile.TemporaryDirectory() as work, patch('scripts.cutover_transfer.subprocess.Popen', return_value=worker), patch('builtins.print'):
            with self.assertRaises(KeyboardInterrupt):
                isolated_restore({}, work)
            worker.terminate.assert_called_once()

    def test_activation_refuses_local_application(self):
        from scripts.cutover_transfer import activate_primary
        with self.assertRaisesMessage(ValueError, 'only in Render'):
            activate_primary('cutover_trial_' + 'a' * 32, '0' * 64)

    def test_conflicting_media_is_never_replaced(self):
        from scripts.cutover_transfer import install_verified_media
        with tempfile.TemporaryDirectory() as work:
            package = self.make_package(work)
            staged = Path(work) / 'staged'
            manifest = unpack_bundle(package, staged)
            media = Path(work) / 'live'; media.mkdir()
            (media / 'test.pdf').write_bytes(b'KEEP-ORIGINAL')
            with self.assertRaisesMessage(ValueError, 'conflicts'):
                install_verified_media(staged, media, manifest)
            self.assertEqual((media / 'test.pdf').read_bytes(), b'KEEP-ORIGINAL')

    def test_media_install_preserves_exact_content_and_is_repeatable(self):
        from scripts.cutover_transfer import install_verified_media
        with tempfile.TemporaryDirectory() as work:
            package = self.make_package(work)
            staged = Path(work) / 'staged'
            manifest = unpack_bundle(package, staged)
            media = Path(work) / 'live'
            install_verified_media(staged, media, manifest)
            install_verified_media(staged, media, manifest)
            self.assertEqual((media / 'test.pdf').read_bytes(), b'TEST-ATTACHMENT')

    def test_primary_with_existing_orders_is_never_replaced(self):
        from unittest.mock import MagicMock
        from scripts.cutover_transfer import require_empty_primary
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        with self.assertRaisesMessage(ValueError, 'already contains bookings'):
            require_empty_primary(connection)

    def test_empty_primary_passes_read_only_guard(self):
        from unittest.mock import MagicMock
        from scripts.cutover_transfer import require_empty_primary
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (0,)
        require_empty_primary(connection)
        cursor.execute.assert_called_once_with('SELECT count(*) FROM public.bookings_booking')

    def test_primary_staging_refuses_local_application(self):
        from scripts.cutover_transfer import stage_primary
        with self.assertRaisesMessage(ValueError, 'only in Render'):
            stage_primary('unused.zip', '0' * 64)

    def test_timestamp_microseconds_survive_serialization(self):
        from datetime import datetime, timezone
        from customers.models import Customer
        from django.core import serializers
        from scripts.cutover_transfer import serialize_record
        timestamp = datetime(2026, 1, 2, 3, 4, 5, 123, tzinfo=timezone.utc)
        obj = Customer(pk=123, created_at=timestamp, updated_at=timestamp)
        record = serialize_record(obj)
        self.assertEqual(record['fields']['created_at'], '2026-01-02T03:04:05.000123Z')
        restored = next(serializers.deserialize('json', json.dumps([record]))).object
        self.assertEqual(restored.created_at, timestamp)
        self.assertEqual(serialize_record(restored), record)

    def test_import_refuses_normal_application_settings(self):
        from scripts.cutover_transfer import load_into_new_database
        with self.assertRaisesMessage(ValueError, 'non-rehearsal'):
            load_into_new_database('default', Path('unused'), {})

    def make_package(self, folder, corrupt=False, extra=None):
        records = b'[]\n'
        data = b'TEST-ATTACHMENT'
        manifest = {'format': 1, 'models': {}, 'records_sha256': hashlib.sha256(records).hexdigest(),
                    'files': {'test.pdf': {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}}}
        package = Path(folder) / 'package.zip'
        with ZipFile(package, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('records.jsonl', b'changed' if corrupt else records)
            archive.writestr('media/test.pdf', data)
            if extra: archive.writestr(extra, b'UNEXPECTED')
        return package

    def test_valid_package_preserves_attachment_bytes(self):
        with tempfile.TemporaryDirectory() as work:
            package = self.make_package(work)
            target = Path(work) / 'unpacked'
            unpack_bundle(package, target)
            self.assertEqual((target / 'media/test.pdf').read_bytes(), b'TEST-ATTACHMENT')

    def test_path_traversal_and_windows_paths_are_rejected(self):
        for name in ('../private', '/private', 'C:/private', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)

    def test_corrupted_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            package = self.make_package(work, corrupt=True)
            with self.assertRaisesMessage(ValueError, 'checksum'):
                unpack_bundle(package, Path(work) / 'unpacked')

    def test_unexpected_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            package = self.make_package(work, extra='unlisted.txt')
            with self.assertRaisesMessage(ValueError, 'manifest'):
                unpack_bundle(package, Path(work) / 'unpacked')

    def test_existing_target_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as work:
            target = Path(work) / 'existing'; target.mkdir()
            evidence = target / 'keep.txt'; evidence.write_text('KEEP')
            with self.assertRaisesMessage(ValueError, 'must not exist'):
                local_rehearsal(Path(work) / 'absent.zip', target)
            self.assertEqual(evidence.read_text(), 'KEEP')

    def test_json_key_order_does_not_change_verification(self):
        self.assertEqual(canonical_record({'b': 2, 'a': 1}), canonical_record({'a': 1, 'b': 2}))
