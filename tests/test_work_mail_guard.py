from unittest.mock import patch

from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings

from config.work_mail import GuardedWorkMailBackend, WorkMailBlocked


@override_settings(WORK_MAIL_MODE='test-only', DEFAULT_FROM_EMAIL='sender@example.com')
class WorkMailGuardTests(SimpleTestCase):
    def backend(self):
        with patch('config.work_mail.load_work_mail', return_value={
            'sender': 'sender@example.com', 'password': 'fake-password', 'test_recipient': 'operator@example.com',
        }):
            return GuardedWorkMailBackend()

    @patch('django.core.mail.backends.smtp.EmailBackend.send_messages', return_value=1)
    def test_only_operator_recipient_can_reach_smtp(self, send):
        message = EmailMessage('Test', 'Invented', to=['Operator <operator@example.com>'])
        self.assertEqual(self.backend().send_messages([message]), 1)
        send.assert_called_once()

    @patch('django.core.mail.backends.smtp.EmailBackend.send_messages')
    def test_to_cc_bcc_and_mixed_batches_are_blocked_before_smtp(self, send):
        for field in ('to', 'cc', 'bcc'):
            message = EmailMessage('Test', 'Invented', to=['operator@example.com'])
            setattr(message, field, ['customer@example.com'])
            with self.subTest(field=field), self.assertRaises(WorkMailBlocked):
                self.backend().send_messages([EmailMessage('Allowed', 'Test', to=['operator@example.com']), message])
        send.assert_not_called()

    @patch('django.core.mail.backends.smtp.EmailBackend.send_messages')
    def test_missing_credentials_do_not_fake_success(self, send):
        with patch('config.work_mail.load_work_mail', return_value={}):
            backend = GuardedWorkMailBackend()
        with self.assertRaises(WorkMailBlocked):
            backend.send_messages([EmailMessage('Test', 'Invented', to=['operator@example.com'])])
        send.assert_not_called()

    @override_settings(WORK_MAIL_MODE='blocked')
    @patch('django.core.mail.backends.smtp.EmailBackend.send_messages')
    def test_explicit_blocked_mode_sends_nothing(self, send):
        with self.assertRaises(WorkMailBlocked):
            self.backend().send_messages([EmailMessage('Test', 'Invented', to=['operator@example.com'])])
        send.assert_not_called()

    @override_settings(WORK_MAIL_MODE='live')
    @patch('django.core.mail.backends.smtp.EmailBackend.send_messages', return_value=1)
    def test_live_mode_requires_explicit_setting(self, send):
        self.assertEqual(self.backend().send_messages([EmailMessage('Test', 'Invented', to=['customer@example.com'])]), 1)
