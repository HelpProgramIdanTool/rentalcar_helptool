"""Superuser-only staging of a private rehearsal package; never imports data."""
import hashlib
from pathlib import Path
import uuid
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from zipfile import is_zipfile


@admin.site.admin_view
@never_cache
@require_http_methods(['GET', 'POST'])
def upload_package(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Owner access required')
    error = ''
    result = None
    if request.method == 'POST':
        incoming = request.FILES.get('package')
        if not incoming or incoming.size > 512 * 1024**2:
            error = 'Выберите пакет ZIP размером не более 512 МБ.'
        elif not is_zipfile(incoming):
            error = 'Нужен ZIP-пакет переноса.'
        else:
            incoming.seek(0)
            directory = Path(settings.MEDIA_ROOT).parent / 'backup-private' / 'cutover-incoming'
            directory.mkdir(parents=True, exist_ok=True)
            destination = directory / (uuid.uuid4().hex + '.zip')
            digest = hashlib.sha256()
            try:
                with destination.open('xb') as output:
                    for chunk in incoming.chunks():
                        output.write(chunk)
                        digest.update(chunk)
                destination.chmod(0o600)
            except Exception:
                destination.unlink(missing_ok=True)
                raise
            result = {'path': str(destination), 'sha256': digest.hexdigest()}
    return render(request, 'admin/cutover_upload.html', {'error': error, 'result': result})
