import importlib
import os
import subprocess
import sys
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class RenderSettingsTests(SimpleTestCase):
    def test_deployment_check_passes_without_email_credentials(self):
        environment = {
            **os.environ,
            'DJANGO_SETTINGS_MODULE': 'config.render_settings',
            'DJANGO_SECRET_KEY': 'test-only-not-a-real-secret-' + 'x' * 60,
            'RENDER_EXTERNAL_HOSTNAME': 'example-test.onrender.com',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'DJANGO_MEDIA_ROOT': '/var/data/private_uploads',
            'GMAIL_ADDRESS': '',
            'GMAIL_APP_PASSWORD': '',
            'DJANGO_ALLOWED_HOSTS': '',
        }
        result = subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
            env=environment, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def load(self, **changes):
        environment = {
            'DJANGO_SECRET_KEY': 'test-only-not-a-real-secret-' + 'x' * 60,
            'RENDER_EXTERNAL_HOSTNAME': 'example-test.onrender.com',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'DJANGO_MEDIA_ROOT': '/var/data/private_uploads',
        }
        environment.update(changes)
        with patch.dict(os.environ, environment, clear=True):
            # A fresh module prevents a failed import from retaining prior values.
            spec = importlib.util.find_spec('config.render_settings')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

    def test_safe_server_settings_and_private_file_storage(self):
        settings = self.load()
        self.assertFalse(settings.DEBUG)
        self.assertEqual(settings.ALLOWED_HOSTS, ['example-test.onrender.com'])
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(settings.MIDDLEWARE[1], 'whitenoise.middleware.WhiteNoiseMiddleware')
        self.assertNotIn('console', str(settings.MAILERS))

    def test_missing_or_unsafe_configuration_stops_startup(self):
        for changes in (
            {'DJANGO_SECRET_KEY': ''},
            {'DJANGO_SECRET_KEY': 'django-insecure-' + 'x' * 60},
            {'DATABASE_URL': ''},
            {'DATABASE_URL': 'sqlite:///temporary.db'},
            {'DJANGO_MEDIA_ROOT': ''},
            {'DJANGO_MEDIA_ROOT': 'temporary-files'},
            {'RENDER_EXTERNAL_HOSTNAME': ''},
            {'DJANGO_ALLOWED_HOSTS': '*'},
        ):
            with self.subTest(changes=changes), self.assertRaises(ImproperlyConfigured):
                self.load(**changes)
