from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override, gettext
from quotes.forms import FirstInquiryForm
from .models import OperatorPreference, Customer


class OperatorLanguageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='language-test')
        self.client.force_login(self.user)

    def test_russian_default_and_three_languages_survive_new_session(self):
        url = reverse('customers:list')
        response = self.client.get(url)
        self.assertEqual(response.headers['Content-Language'], 'ru')
        for language, heading in [('en','Customers'), ('pl','Klienci'), ('ru','Клиенты')]:
            self.client.post(reverse('operator_language'), {'language':language, 'next':url})
            self.client.logout()
            self.client.force_login(self.user)
            response = self.client.get(url)
            self.assertContains(response, heading)
            self.assertEqual(response.headers['Content-Language'], language)

    def test_form_labels_use_catalog_but_customer_data_stays_exact(self):
        for language, label in [('en','Pickup date'), ('pl','Data odbioru')]:
            with override(language):
                self.assertEqual(str(FirstInquiryForm.base_fields['pickup_date'].label), label)
        customer = Customer.objects.create(first_name='Польша', last_name='Клиент')
        self.client.post(reverse('operator_language'), {'language':'en'})
        response = self.client.get(reverse('customers:list'))
        self.assertContains(response, 'Польша Клиент')
        customer.refresh_from_db()
        self.assertEqual(customer.preferred_language, '')

    def test_invalid_language_and_external_redirect_are_rejected(self):
        response = self.client.post(reverse('operator_language'), {'language':'xx', 'next':'https://example.com'})
        self.assertEqual(response.url, '/')
        self.assertFalse(OperatorPreference.objects.filter(user=self.user).exists())
