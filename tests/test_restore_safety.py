import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

from django.test import SimpleTestCase

from scripts.test_render_restore import extract_uploads, validate_target, verify_manifest


class RestoreSafetyTests(SimpleTestCase):
    def test_original_server_and_external_alias_are_rejected(self):
        source = {'HOST': 'dpg-original', 'NAME': 'working'}
        for host in ('dpg-original', 'dpg-original.frankfurt-postgres.render.com'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                validate_target(source, {'HOST': host, 'NAME': 'rentalcar_restore_test',
                                        'ENGINE': 'django.db.backends.postgresql'})

    def test_only_explicitly_named_postgresql_test_database_is_accepted(self):
        source = {'HOST': 'dpg-original'}
        target = {'HOST': 'dpg-test', 'NAME': 'rentalcar_restore_test_abcd', 'ENGINE': 'django.db.backends.postgresql'}
        validate_target(source, target)
        for changes in ({'NAME': 'working'}, {'ENGINE': 'django.db.backends.sqlite3'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_target(source, {**target, **changes})

    def test_tampering_and_unexpected_manifest_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            files = {}
            for name in ('database.dump', 'private_uploads.tar.gz'):
                (folder / name).write_bytes(b'invented-backup')
                files[name] = {'bytes': 15, 'sha256': hashlib.sha256(b'invented-backup').hexdigest()}
            (folder / 'manifest.json').write_text(json.dumps({'format': 1, 'files': files}))
            verify_manifest(folder)
            (folder / 'database.dump').write_bytes(b'tampered-backup')
            with self.assertRaises(ValueError):
                verify_manifest(folder)
            files['../private-key'] = files.pop('database.dump')
            (folder / 'manifest.json').write_text(json.dumps({'format': 1, 'files': files}))
            with self.assertRaises(ValueError):
                verify_manifest(folder)

    def test_upload_file_restores_exact_content_and_rejects_escape_or_links(self):
        for name, kind in (('private_uploads/test.pdf', tarfile.REGTYPE),
                           ('../escape', tarfile.REGTYPE),
                           ('private_uploads/link', tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                archive_path = folder / 'uploads.tar.gz'
                with tarfile.open(archive_path, 'w:gz') as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = '/etc/secrets/rclone.conf' if kind == tarfile.SYMTYPE else ''
                    member.size = 8 if kind == tarfile.REGTYPE else 0
                    archive.addfile(member, io.BytesIO(b'test-pdf') if member.size else None)
                destination = folder / 'output'
                destination.mkdir()
                if name == 'private_uploads/test.pdf':
                    self.assertEqual(extract_uploads(archive_path, destination), 1)
                    self.assertEqual((destination / name).read_bytes(), b'test-pdf')
                else:
                    with self.assertRaises(ValueError):
                        extract_uploads(archive_path, destination)
