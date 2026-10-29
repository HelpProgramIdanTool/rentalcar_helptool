"""Render-only settings. Local manage.py continues to use config.settings."""
import os
from pathlib import Path, PurePosixPath

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403


def required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'Render requires {name}.')
    return value


SECRET_KEY = required('DJANGO_SECRET_KEY')
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('Generate a new, long DJANGO_SECRET_KEY on Render.')

DEBUG = False
ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if host.strip()
]
render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if render_host:
    ALLOWED_HOSTS.append(render_host)
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('Set an exact Render hostname in DJANGO_ALLOWED_HOSTS.')

DATABASES = {'default': dj_database_url.parse(required('DATABASE_URL'), conn_max_age=60)}
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Render requires a PostgreSQL DATABASE_URL.')

MEDIA_ROOT = Path(required('DJANGO_MEDIA_ROOT'))
if not PurePosixPath(str(MEDIA_ROOT).replace('\\', '/')).is_absolute():
    raise ImproperlyConfigured('DJANGO_MEDIA_ROOT must be an absolute persistent disk path.')

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MIDDLEWARE = [*MIDDLEWARE]
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS]

# Never print customer emails to the server log if SMTP has not been configured.
SILENCED_SYSTEM_CHECKS = []
if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD):
    MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.dummy.EmailBackend'}}
    # Email is deliberately disabled for the initial test deployment.
    # Suppress only this known check; keep every other deployment check active.
    SILENCED_SYSTEM_CHECKS = ['mail.E001']
