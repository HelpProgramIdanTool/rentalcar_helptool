from types import SimpleNamespace
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class OfferHeaderTests(SimpleTestCase):
    def test_email_has_a_prominent_number_before_intro_in_both_languages(self):
        for english in [False,True]:
            html=render_to_string('quotes/quote_preview.html',dict(is_email=True,is_english=english,is_ltr=english,
                quote=SimpleNamespace(quote_number='TEST-OFFER-4321',customer='TEST CUSTOMER'),
                introduction_blocks=[SimpleNamespace(block_key='INTRO',title='TEST INTRO',content_html='TEST INTRO BODY')]))
            self.assertIn('class="offer-reference"',html)
            self.assertIn('font-size:22px;font-weight:800',html)
            self.assertLess(html.index('class="offer-reference"'),html.index('TEST INTRO'))
            self.assertIn('>TEST-OFFER-4321</strong>',html)
