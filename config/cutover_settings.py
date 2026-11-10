"""Subprocess-only settings: no connection to the authoritative database."""
import json
import os
import re
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403

try:
    cutover_database = json.loads(os.environ['CUTOVER_ISOLATED_DATABASE'])
    cutover_directory = Path(os.environ['CUTOVER_ISOLATED_DIRECTORY']).resolve()
except (KeyError, ValueError, TypeError):
    raise ImproperlyConfigured('Isolated rehearsal configuration is required') from None

if cutover_database.get('ENGINE') == 'django.db.backends.sqlite3':
    if Path(cutover_database.get('NAME', '')).resolve() != cutover_directory / 'restored.sqlite3':
        raise ImproperlyConfigured('Unexpected SQLite rehearsal target')
elif cutover_database.get('ENGINE') == 'django.db.backends.postgresql':
    if not re.fullmatch(r'-c search_path=cutover_trial_[a-f0-9]{32}',
                        cutover_database.get('OPTIONS', {}).get('options', '')):
        raise ImproperlyConfigured('A new rehearsal schema is required')
else:
    raise ImproperlyConfigured('Unsupported rehearsal database')

DATABASES = {'default': cutover_database}
MEDIA_ROOT = cutover_directory / 'media'
MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}}
CUTOVER_ISOLATED_WORKER = True
