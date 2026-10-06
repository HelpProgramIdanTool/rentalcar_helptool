from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.test import SimpleTestCase

from config.email_addresses import parse_email_addresses
from suppliers.models import Supplier


class EmailAddressTests(SimpleTestCase):
    def test_multiple_addresses_and_duplicates(self):
        self.assertEqual(parse_email_addresses(' first@example.com; second@example.com, FIRST@example.com; '),
                         ['first@example.com', 'second@example.com'])
        self.assertEqual(parse_email_addresses(''), [])

    def test_invalid_recipient_rejects_entire_list(self):
        for value in ('ok@example.com; broken', '; ;', 'a@example.com\r\nBcc: b@example.com', r'a\@example.com'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_email_addresses(value)

    def test_supplier_settings_form_accepts_two_emails(self):
        form_type = modelform_factory(Supplier, fields=['booking_email', 'changes_email', 'settlement_email'])
        form = form_type(data={'booking_email':'one@example.com; two@example.com','changes_email':'change@example.com; manager@example.com','settlement_email':'finance@example.com; manager@example.com'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.fields['booking_email'].widget.input_type, 'text')
        self.assertEqual(form.fields['settlement_email'].widget.input_type, 'text')
        form = form_type(data={'booking_email':'one@example.com; broken'})
        self.assertFalse(form.is_valid())
