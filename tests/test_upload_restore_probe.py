import hashlib
from pathlib import Path
import tarfile
import tempfile

from django.test import SimpleTestCase

from scripts.test_render_restore import extract_uploads
from scripts.test_upload_restore import check_restored_pdf, create_probe


class UploadRestoreProbeTests(SimpleTestCase):
    def test_generated_pdf_recovers_from_archive_with_exact_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'media'
            media.mkdir()
            existing = media / 'existing.pdf'
            existing.write_bytes(b'invented-existing-file')
            source, token = create_probe(media)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            archive_path = root / 'uploads.tar.gz'
            with tarfile.open(archive_path, 'w:gz') as archive:
                archive.add(media, arcname='private_uploads')
            destination = root / 'restored'
            destination.mkdir()
            self.assertEqual(extract_uploads(archive_path, destination), 2)
            restored = destination / 'private_uploads' / source.relative_to(media)
            check_restored_pdf(restored, digest, token)
            self.assertEqual(existing.read_bytes(), b'invented-existing-file')
            self.assertEqual(source.read_bytes(), restored.read_bytes())

    def test_modified_or_missing_pdf_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, token = create_probe(Path(temporary))
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            source.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                check_restored_pdf(source, digest, token)
            with self.assertRaises(ValueError):
                check_restored_pdf(source.with_name('missing.pdf'), digest, token)
