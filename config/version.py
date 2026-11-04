from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

APP_VERSION = '2026.11.04.1'


def app_version(request):
    return {'app_version': APP_VERSION}


@login_required
def version_history(request):
    content = (Path(__file__).resolve().parent.parent / 'CHANGELOG.md').read_text(encoding='utf8')
    return render(request, 'bookings/version_history.html', {'version_history': content})
