from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from bookings.models import Booking
from quotes.models import Quote
from suppliers.models import Supplier
from .models import Customer, ReferralContact, ReferralEmail
from .views import ContactForm


class ContactFormTests(SimpleTestCase):
    def test_multiple_addresses_are_validated_normalized_and_deduplicated(self):
        form = ContactForm({'name': 'TEST CONTACT', 'emails': 'ONE@example.com\none@example.com\ntwo@example.com'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['emails'], ['one@example.com', 'two@example.com'])
        form = ContactForm({'name': 'TEST', 'emails': 'not an email'})
        self.assertFalse(form.is_valid())


class ContactViewsTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='contact-test'))
        self.contact = ReferralContact.objects.create(name='TEST CONTACT')
        ReferralEmail.objects.create(contact=self.contact, email='one@example.com')
        ReferralEmail.objects.create(contact=self.contact, email='two@example.com')
        self.supplier = Supplier.objects.create(supplier_code='CONTACT-TEST', supplier_name='TEST SUPPLIER')
        self.customer = Customer.objects.create(first_name='TEST RENTER', last_name='NAME', email='one@example.com')
        self.booking = Booking.objects.create(customer=self.customer, supplier=self.supplier, referral_contact=self.contact)
        self.cancelled = Booking.objects.create(customer=self.customer, supplier=self.supplier,
            referral_contact=self.contact, status='CANCELLED')
        self.quote = Quote.objects.create(customer=self.customer, referral_contact=self.contact,
            pickup_datetime=timezone.now(), return_datetime=timezone.now()+timedelta(days=1))

    def test_search_each_email_or_name_counts_same_contact_once(self):
        for search in ['TEST CONTACT', 'one@example.com', 'two@example.com']:
            response = self.client.get(reverse('customers:contacts'), {'q': search})
            rows = response.context['rows']
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]['offers'], rows[0]['bookings'], rows[0]['cancelled']), (1,1,1))
        self.assertIsNone(self.booking.sub_agent)
        self.assertEqual(self.customer.first_name, 'TEST RENTER')

    def test_counts_and_filtered_lists_use_identical_creation_period(self):
        tomorrow = (timezone.localdate()+timedelta(days=1)).isoformat()
        response = self.client.get(reverse('customers:contacts'), {'start': tomorrow})
        self.assertEqual(response.context['rows'][0]['bookings'], 0)
        for kind, pk in [('offers', self.quote.pk), ('bookings', self.booking.pk), ('cancelled', self.cancelled.pk)]:
            response = self.client.get(reverse('customers:contact_detail', args=[self.contact.pk]), {'kind': kind})
            self.assertEqual(list(response.context['records'].values_list('pk', flat=True)), [pk])

    def test_historical_link_requires_confirmation_and_does_not_overwrite_other_contact(self):
        old = Booking.objects.create(customer=self.customer, supplier=self.supplier)
        url = reverse('customers:contact_detail', args=[self.contact.pk])
        self.client.get(url, {'link': '1'})
        old.refresh_from_db()
        self.assertIsNone(old.referral_contact_id)
        self.client.post(url, {'action':'link', 'selected':[str(old.pk)]})
        old.refresh_from_db()
        self.assertIsNone(old.referral_contact_id)
        self.client.post(url, {'action':'link', 'selected':[str(old.pk)], 'confirm':'yes'})
        old.refresh_from_db()
        self.assertEqual(old.referral_contact_id, self.contact.pk)
        self.assertEqual(old.customer_id, self.customer.pk)

    def test_duplicate_preserves_contact_and_country(self):
        self.quote.rental_country = 'CZ'
        self.quote.save()
        self.client.post(reverse('quotes:duplicate_quote', args=[self.quote.quote_number]))
        new = Quote.objects.exclude(pk=self.quote.pk).get()
        self.assertEqual(new.referral_contact_id, self.contact.pk)
        self.assertEqual(new.rental_country, 'CZ')
