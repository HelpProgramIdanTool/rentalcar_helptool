from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

APP_VERSION = '2026.11.14.1'


def app_version(request):
    from bookings.statistics import can_view_statistics
    return {'app_version': APP_VERSION, 'can_view_statistics': can_view_statistics(request.user)}


@login_required
def version_history(request):
    content = (Path(__file__).resolve().parent.parent / 'CHANGELOG.md').read_text(encoding='utf8')
    return render(request, 'bookings/version_history.html', {'version_history': content})
