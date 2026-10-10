from unittest.mock import patch
from django.test import SimpleTestCase
from .models import Quote
from .localization import offer_subject
from .email_forms import EmailSubjectForm


class SubjectDefaultTests(SimpleTestCase):
    @patch('quotes.localization.presentation_for', return_value={'default_subject': 'TEST-SUBJECT'})
    def test_default_is_read_from_template_and_shown_in_form(self, presentation):
        quote = Quote(language='Hebrew', quote_number='TEST-1')
        self.assertEqual(offer_subject(quote), 'TEST-SUBJECT')
        self.assertEqual(EmailSubjectForm(instance=quote)['email_subject'].value(), 'TEST-SUBJECT')
        quote.email_subject = 'Custom subject'
        self.assertEqual(offer_subject(quote), 'Custom subject')
        self.assertEqual(EmailSubjectForm(instance=quote)['email_subject'].value(), 'Custom subject')
        self.assertEqual(EmailSubjectForm({'email_subject': ''}, instance=quote)['email_subject'].value(), '')
