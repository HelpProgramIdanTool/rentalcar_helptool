from django.test import SimpleTestCase
from django.urls import resolve


class ProjectSetupTests(SimpleTestCase):
    def test_admin_url_is_connected(self):
        match = resolve("/admin/")

        self.assertEqual(match.app_name, "admin")

