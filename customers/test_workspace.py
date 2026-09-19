from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from quotes.models import Quote
from .models import Customer


class CustomerWorkspaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workspace", password="test-pass")
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(first_name="Anna", last_name="Cohen", email="shared@example.com", phone_2="4822222", phone_3="4833333")
        self.other = Customer.objects.create(email="shared@example.com")
        pickup = timezone.now() + timedelta(days=10)
        self.quote = Quote.objects.create(customer=self.customer, pickup_datetime=pickup, return_datetime=pickup+timedelta(days=3))
        self.other_quote = Quote.objects.create(customer=self.other, pickup_datetime=pickup, return_datetime=pickup+timedelta(days=4))

    def test_authentication_required(self):
        self.client.logout()
        for url in (reverse("customers:list"), reverse("customers:detail", args=[self.customer.pk])):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_search_name_email_and_secondary_phones(self):
        for search, count in (("Anna Cohen", 1), ("shared@example.com", 2), ("4822222", 1), ("4833333", 1), ("missing", 0)):
            with self.subTest(search=search):
                response = self.client.get(reverse("customers:list"), {"q": search})
                self.assertEqual(response.context["page_obj"].paginator.count, count)

    def test_nameless_customer_has_usable_detail_and_offer_links(self):
        response = self.client.get(reverse("customers:list"))
        self.assertContains(response, reverse("customers:detail", args=[self.other.pk]))
        self.assertContains(response, reverse("quotes:customer_offer", args=[self.other.pk]))
        self.assertContains(response, "shared@example.com")

    def test_detail_only_shows_selected_customers_offers(self):
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertContains(response, self.quote.quote_number)
        self.assertNotContains(response, self.other_quote.quote_number)
        self.assertContains(response, reverse("quotes:duplicate_quote", args=[self.quote.quote_number]))
        self.assertEqual(self.client.get(reverse("customers:detail", args=[999999])).status_code, 404)

    def test_copy_preserves_original_and_customer(self):
        original_return = self.quote.return_datetime
        response = self.client.post(reverse("quotes:duplicate_quote", args=[self.quote.quote_number]))
        duplicate = Quote.objects.exclude(pk__in=[self.quote.pk, self.other_quote.pk]).get()
        self.assertEqual(duplicate.customer_id, self.customer.pk)
        self.assertNotEqual(duplicate.quote_number, self.quote.quote_number)
        self.assertEqual(duplicate.return_datetime, original_return)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.return_datetime, original_return)
        self.assertRedirects(response, reverse("quotes:edit_quote", args=[duplicate.quote_number]))

    def test_pagination_retains_search(self):
        Customer.objects.bulk_create([Customer(first_name="Findme") for _ in range(26)])
        response = self.client.get(reverse("customers:list"), {"q": "Findme"})
        self.assertContains(response, "q=Findme&amp;page=2")
        response = self.client.get(reverse("customers:list"), {"q": "Findme", "page": 2})
        self.assertEqual(len(response.context["page_obj"]), 1)
