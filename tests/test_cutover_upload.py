from io import BytesIO
import tempfile
from pathlib import Path
from zipfile import ZipFile
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse


class CutoverUploadTests(TestCase):
    def test_anonymous_and_staff_without_owner_rights_cannot_upload(self):
        url = reverse('cutover_upload')
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user('test-staff', is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_owner_upload_stages_only_private_file(self):
        owner = get_user_model().objects.create_superuser('test-owner', 'test@example.test', 'test-password')
        self.client.force_login(owner)
        data = BytesIO()
        with ZipFile(data, 'w') as archive:
            archive.writestr('test.txt', 'TEST')
        with tempfile.TemporaryDirectory() as work, override_settings(MEDIA_ROOT=Path(work) / 'private_uploads'):
            response = self.client.post(reverse('cutover_upload'), {'package':SimpleUploadedFile('test.zip', data.getvalue())})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['result']['sha256'])
            self.assertTrue(Path(response.context['result']['path']).is_file())
            self.assertNotIn('/media/', response.context['result']['path'])

    def test_invalid_upload_is_rejected(self):
        owner = get_user_model().objects.create_superuser('test-owner', 'test@example.test', 'test-password')
        self.client.force_login(owner)
        response = self.client.post(reverse('cutover_upload'), {'package':SimpleUploadedFile('test.zip', b'not a zip')})
        self.assertIsNone(response.context['result'])
        self.assertTrue(response.context['error'])
