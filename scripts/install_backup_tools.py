"""Install a verified, pinned rclone binary on the Render persistent disk."""
import hashlib
import io
import os
from pathlib import Path
import platform
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen
import zipfile

VERSION = '1.75.2'
# From the official v1.75.2 SHA256SUMS, fetched during setup.
LINUX_SHA256 = '349ac8fba6ff65d6247043f1750cdcb518ec5d500ef91463a10d37c0ccdf3702'
DESTINATION = Path('/var/data/backup-tools/rclone')


def download_archive(filename):
    sources = (
        f'https://downloads.rclone.org/v{VERSION}/{filename}',
        f'https://github.com/rclone/rclone/releases/download/v{VERSION}/{filename}',
    )
    for number, url in enumerate(sources, 1):
        try:
            request = Request(url, headers={'User-Agent': 'RentalCar-Backup-Installer/1.0'})
            with urlopen(request, timeout=120) as response:
                return response.read()
        except (URLError, TimeoutError):
            print(f'Official download source {number} unavailable.')
    raise RuntimeError('Both official download sources failed; nothing installed.')


def verified_binary(archive, checksums, filename):
    expected = None
    for line in checksums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip('*') == filename:
            expected = parts[0].lower()
            break
    if expected is None or hashlib.sha256(archive).hexdigest() != expected:
        raise ValueError('Official archive checksum did not match; nothing installed.')
    member = filename.removesuffix('.zip') + '/rclone'
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        # Read only the expected executable. Never extract archive paths.
        return package.read(member)


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise SystemExit('Run this installer in Render Shell (Linux x86_64).')
    if not os.path.ismount('/var/data'):
        raise SystemExit('Persistent disk /var/data is not mounted; nothing installed.')
    filename = f'rclone-v{VERSION}-linux-amd64.zip'
    archive = download_archive(filename)
    checksums = f'{LINUX_SHA256}  {filename}'
    binary = verified_binary(archive, checksums, filename)
    DESTINATION.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=DESTINATION.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(binary)
        temporary.chmod(0o700)
        os.replace(temporary, DESTINATION)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f'rclone {VERSION} installed: {DESTINATION}')
    print('No credentials uploaded. No backup schedule enabled.')


if __name__ == '__main__':
    main()
