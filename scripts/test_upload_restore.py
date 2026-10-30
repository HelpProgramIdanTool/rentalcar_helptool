"""End-to-end recovery of an invented PDF from encrypted Drive backups."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import uuid

import pymupdf
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.render_backup import PRIVATE, RCLONE, STATE, prepare_config, run_backup, run_command, write_json
from scripts.test_render_restore import extract_uploads, verify_manifest


def create_probe(media):
    token = 'TEST-BACKUP-' + uuid.uuid4().hex
    buffer = io.BytesIO()
    document = canvas.Canvas(buffer)
    document.setTitle('Invented PDF for backup recovery verification')
    document.drawString(50, 780, 'BACKUP RECOVERY TEST - NO CUSTOMER DATA')
    document.drawString(50, 750, token)
    document.save()
    directory = media / '_backup_verification'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / (token + '.pdf')
    with path.open('xb') as handle:
        handle.write(buffer.getvalue())
    path.chmod(0o600)
    return path, token


def check_restored_pdf(path, original_hash, token):
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != original_hash:
        raise ValueError('Restored PDF is missing or different from its original.')
    with pymupdf.open(path) as document:
        text = ''.join(page.get_text() for page in document)
    if token not in text:
        raise ValueError('The restored PDF does not contain the expected test text.')


def main():
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings' or not os.path.ismount('/var/data'):
        raise SystemExit('Run only in Render Shell with its persistent disk.')
    from django.conf import settings
    media = Path(settings.MEDIA_ROOT)
    if media != Path('/var/data/private_uploads') or media.is_symlink():
        raise ValueError('Unexpected upload directory.')
    source, token = create_probe(media)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    relative = source.relative_to(media)
    print('Invented PDF created. Making a new encrypted backup...', flush=True)
    run_backup()
    status = json.loads(STATE.read_text())
    remote = status.get('remote', '')
    if status.get('result') != 'success' or not re.fullmatch(r'backupcrypt:scheduled/[0-9TZ-]+-[a-f0-9]{8}', remote):
        raise ValueError('No successful backup available for this test.')
    work = PRIVATE / ('pdf-restore-test-' + uuid.uuid4().hex[:12])
    work.mkdir(mode=0o700, parents=True)
    downloaded, restored = work / 'downloaded', work / 'restored'
    downloaded.mkdir(mode=0o700)
    restored.mkdir(mode=0o700)
    print('Downloading, decrypting and restoring files into a separate directory...', flush=True)
    with (work / 'test.log').open('w') as log:
        run_command([RCLONE, '--config', str(prepare_config()), 'copy', remote, str(downloaded)], log)
    verify_manifest(downloaded)
    count = extract_uploads(downloaded / 'private_uploads.tar.gz', restored)
    check_restored_pdf(restored / 'private_uploads' / relative, digest, token)
    write_json(work / 'report.json', {'result': 'success', 'completed_utc': datetime.now(timezone.utc).isoformat(),
                                    'backup': remote, 'restored_files': count, 'test_pdf_sha256': digest})
    # Remove only the unique invented file created by this invocation.
    source.unlink()
    print('PDF RESTORE SUCCESS: downloaded, decrypted, exact SHA-256 match, readable PDF.', flush=True)
    print('Invented source file removed. Existing vouchers and both databases were not modified.', flush=True)
    print('Private report: ' + str(work / 'report.json'), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('PDF RESTORE TEST FAILED (' + type(error).__name__ + '). No existing vouchers removed.', flush=True)
        raise SystemExit(1)
