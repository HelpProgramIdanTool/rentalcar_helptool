from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from .models import Quote


class QuoteListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="list-user", password="test-pass")
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(first_name="Anna", last_name="Cohen", email="anna@example.com", phone_1="48123456789")
        self.pickup = timezone.make_aware(datetime(2026, 9, 20, 10))
        self.draft = self.make_quote()
        self.sent = self.make_quote(status=Quote.Status.SENT, sent_at=timezone.now())
        self.later = self.make_quote(pickup_datetime=self.pickup + timedelta(days=10), return_datetime=self.pickup + timedelta(days=12))

    def make_quote(self, **overrides):
        values = dict(customer=self.customer, pickup_datetime=self.pickup,
                      return_datetime=self.pickup + timedelta(days=2),
                      pickup_location_text="Warszawa", return_location_text="Kraków")
        values.update(overrides)
        return Quote.objects.create(**values)

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("quotes:quote_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_home_opens_list_and_creation_stays_available(self):
        response = self.client.get(reverse("quotes:home"))
        self.assertTemplateUsed(response, "quotes/quote_list.html")
        self.assertContains(response, self.draft.quote_number)
        self.assertContains(response, reverse("quotes:new_inquiry"))
        self.assertEqual(reverse("quotes:new_inquiry"), "/offers/new/")
        self.assertTemplateUsed(self.client.get(reverse("quotes:new_inquiry")), "quotes/new_inquiry.html")

    def test_search_matches_number_full_name_email_and_phone(self):
        for term in ("Anna Cohen", "anna@example.com", "48123456789", self.sent.quote_number):
            with self.subTest(term=term):
                response = self.client.get(reverse("quotes:quote_list"), {"q": term})
                self.assertIn(self.sent, response.context["page_obj"])
        response = self.client.get(reverse("quotes:quote_list"), {"q": "unknown-client"})
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_filters_combine_and_include_both_date_boundaries(self):
        response = self.client.get(reverse("quotes:quote_list"), {
            "q": "Anna", "status": "SENT", "pickup_from": "2026-09-20", "pickup_to": "2026-09-20",
        })
        self.assertEqual(list(response.context["page_obj"]), [self.sent])

    def test_invalid_filters_show_errors_without_returning_all_quotes(self):
        for query in ({"pickup_from": "bad"}, {"status": "UNKNOWN"},
                      {"pickup_from": "2026-10-01", "pickup_to": "2026-09-01"}):
            response = self.client.get(reverse("quotes:quote_list"), query)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["filters"].errors)
            self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_sort_is_validated(self):
        response = self.client.get(reverse("quotes:quote_list"), {"sort": "-pickup_datetime"})
        self.assertEqual(response.context["page_obj"][0], self.later)
        response = self.client.get(reverse("quotes:quote_list"), {"sort": "not_a_field"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "-created_at")

    def test_pagination_preserves_filters(self):
        for _ in range(24):
            self.make_quote()
        response = self.client.get(reverse("quotes:quote_list"), {"q": "Anna", "status": "DRAFT"})
        self.assertEqual(len(response.context["page_obj"]), 25)
        self.assertContains(response, "q=Anna&amp;status=DRAFT&amp;page=2")
        response = self.client.get(reverse("quotes:quote_list"), {"q": "Anna", "status": "DRAFT", "page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 1)

    def test_staff_can_open_settings_and_existing_lists_from_menu(self):
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(reverse("quotes:quote_list"))
        for name in ("admin:index", "customers:list", "quotes:booking_list"):
            self.assertContains(response, reverse(name))
