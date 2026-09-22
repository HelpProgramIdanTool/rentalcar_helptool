from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from suppliers.models import Supplier, VehicleComparisonClass, VehicleGroup, PriceList, PriceSeason, PriceDayRange, VehicleRate

from .models import Quote, QuoteOption, QuoteTemplate
from .services import (
    HEBREW_EXTRA_NAMES,
    HEBREW_VEHICLE_CLASS_NAMES,
    STANDARD_INCLUDED_ITEMS,
    normalize_included_items,
    _extra_line_name,
    _extra_price,
    _luggage_info,
    _rate_description,
    _quoted_extra_price,
    _service_extra_requests,
    calculate_quote_options,
    ensure_quote_document_blocks,
    ensure_quote_option_presentation,
    vehicle_class_presentation,
)


class FirstInquiryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="idan", password="test-pass")
        self.client.force_login(self.user)
        self.pickup = timezone.now() + timedelta(days=2)
        self.supplier = Supplier.objects.create(
            supplier_code="TEST", supplier_name="Test supplier"
        )
        comparisons = list(VehicleComparisonClass.objects.all()[:2])
        self.form_groups = [
            VehicleGroup.objects.create(
                supplier=self.supplier,
                group_code=f"FORM-{index}",
                group_name=f"Form group {index}",
            )
            for index in (1, 2)
        ]
        for comparison, group in zip(comparisons, self.form_groups):
            comparison.vehicle_groups.add(group)
        price_list = PriceList.objects.create(
            supplier=self.supplier, name="Form prices", version="1",
            effective_from=self.pickup.date() - timedelta(days=1), status="ACTIVE",
        )
        season = PriceSeason.objects.create(
            price_list=price_list, season_code="ALL", season_name="All",
            rental_date_from=self.pickup.date() - timedelta(days=1),
        )
        day_range = PriceDayRange.objects.create(
            price_list=price_list, range_code="ALL", label="All", days_from=1,
        )
        for group in self.form_groups:
            VehicleRate.objects.create(
                season=season, day_range=day_range, vehicle_group=group,
                daily_rate_gross=100,
            )

    def data(self, **changes):
        values = {
            "first_name": "Anna", "last_name": "Nowak", "email": "anna@example.com",
            "phone_1": "+48123123123", "preferred_language": "Hebrew",
            "suppliers": [str(self.supplier.id)],
            "pickup_date": self.pickup.strftime("%d-%m-%Y"),
            "pickup_time": "14:00",
            "return_date": (self.pickup + timedelta(days=3, hours=2)).strftime("%d-%m-%Y"),
            "return_time": "16:00",
            "pickup_city": "Kraków", "pickup_service": "AIRPORT", "vehicle_class": "1",
            "return_city": "Kraków", "return_service": "AIRPORT", "vehicle_classes": ["1", "2"],
            "vehicle_groups": [str(group.id) for group in self.form_groups],
            "extra_choices": ["CHILD_SEAT", "SNOW_CHAINS"], "child_seat_quantity": 2,
            "driver_count": 2,
        }
        values.update(changes)
        return values

    def test_new_inquiry_starts_empty_and_offers_draft_controls(self):
        response = self.client.get(reverse("quotes:new_inquiry"))

        self.assertContains(response, "← На главную")
        self.assertContains(response, f'href="{reverse("quotes:home")}"')
        self.assertContains(response, "Очистить и начать новый запрос")
        self.assertContains(response, "Восстановить черновик")
        self.assertContains(response, "Малые автомобили")
        self.assertContains(response, 'class="message-panel"')
        self.assertContains(response, 'class="form-scroll"')
        self.assertContains(response, "body { margin:0;overflow:hidden; }")
        self.assertContains(response, "position:sticky;top:0")
        self.assertContains(response, 'type="date"')
        self.assertNotContains(response, "data-picker=")
        self.assertContains(response, 'autocomplete="off"')
        self.assertNotContains(response, "restoreDraft();")

    def test_first_email_creates_customer_and_draft_quote(self):
        response = self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self.assertRedirects(response, reverse("quotes:inquiry_saved", args=[quote.quote_number]))
        self.assertEqual(Customer.objects.count(), 1)

        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(quote.rental_days, 4)
        self.assertEqual(quote.extra_requests["CHILD_SEAT"], 2)
        self.assertEqual(quote.pickup_service, "AIRPORT")
        self.assertEqual(quote.requested_suppliers.count(), 1)
        self.assertEqual(quote.requested_vehicle_groups.count(), 2)

    def test_date_calendars_do_not_share_labels_with_manual_inputs(self):
        from html.parser import HTMLParser

        class DateLabels(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.calendars = []
                self.targets = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "label":
                    self.depth += 1
                    self.targets.append(attrs.get("for"))
                if tag == "input" and attrs.get("type") == "date":
                    self.calendars.append((attrs.get("id"), self.depth))

            def handle_endtag(self, tag):
                if tag == "label":
                    self.depth -= 1

        response = self.client.get(reverse("quotes:new_inquiry"))
        parsed = DateLabels()
        parsed.feed(response.content.decode())
        self.assertEqual(parsed.calendars, [("pickup-calendar", 0), ("return-calendar", 0)])
        self.assertIn("id_pickup_date", parsed.targets)
        self.assertIn("id_return_date", parsed.targets)

    def test_offer_can_be_created_without_last_name_using_only_phone(self):
        response = self.client.post(
            reverse("quotes:new_inquiry"),
            self.data(last_name="", email="", phone_1="+48111222333"),
        )

        self.assertEqual(response.status_code, 302)
        customer = Customer.objects.get()
        self.assertEqual(customer.last_name, "")
        self.assertEqual(customer.phone_1, "+48111222333")

    def test_twenty_extra_minutes_do_not_add_a_rental_day(self):
        response = self.client.post(
            reverse("quotes:new_inquiry"),
            self.data(
                pickup_time="14:00",
                return_date=(self.pickup + timedelta(days=2)).strftime("%d-%m-%Y"),
                return_time="14:20",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Quote.objects.get().rental_days, 2)

    def test_more_than_one_extra_hour_adds_a_rental_day(self):
        response = self.client.post(
            reverse("quotes:new_inquiry"),
            self.data(
                pickup_time="14:00",
                return_date=(self.pickup + timedelta(days=2)).strftime("%d-%m-%Y"),
                return_time="15:05",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Quote.objects.get().rental_days, 3)

    def test_city_address_service_is_charged_for_each_side(self):
        from types import SimpleNamespace
        quote = SimpleNamespace(pickup_service="ADDRESS", return_service="ADDRESS")
        self.assertEqual(
            _service_extra_requests(quote, "01"),
            {"CITY_ADDRESS_DELIVERY": 2},
        )
        self.assertEqual(
            _service_extra_requests(quote, "03"),
            {"CITY_ADDRESS_DELIVERY": 2},
        )

    def test_one_rent_airport_fee_is_added_once(self):
        from types import SimpleNamespace
        quote = SimpleNamespace(pickup_service="AIRPORT", return_service="AIRPORT")
        self.assertEqual(
            _service_extra_requests(quote, "02"),
            {"AIRPORT_FEE": 1},
        )

    def test_same_email_reuses_existing_customer(self):
        Customer.objects.create(first_name="Anna", last_name="Old", email="anna@example.com", phone_1="111")
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Customer.objects.get().last_name, "Nowak")

    def test_contact_is_required(self):
        response = self.client.post(reverse("quotes:new_inquiry"), self.data(email="", phone_1=""))
        self.assertContains(response, "Укажите хотя бы e-mail или номер телефона.")
        self.assertEqual(Quote.objects.count(), 0)

    def test_only_one_contact_is_enough_without_other_customer_fields(self):
        from .forms import FirstInquiryForm

        for field, value in (("email", "only@example.com"), ("phone_1", "111"), ("phone_2", "222"), ("phone_3", "333")):
            with self.subTest(field=field):
                data = self.data(first_name="", last_name="", email="", phone_1="", phone_2="", phone_3="", preferred_language="", wants_invoice=True)
                data[field] = value
                form = FirstInquiryForm(data)
                self.assertTrue(form.is_valid(), form.errors)

    def test_nameless_customer_can_save_offer_and_has_contact_label(self):
        response = self.client.post(reverse("quotes:new_inquiry"), self.data(first_name="", last_name="", phone_1=""))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(Quote.objects.get().customer), "anna@example.com")

    def test_customer_offer_prefills_and_keeps_exact_customer_with_shared_email(self):
        Customer.objects.create(first_name="Other", email="shared@example.com")
        selected = Customer.objects.create(first_name="", last_name="", email="shared@example.com", phone_2="222")
        url = reverse("quotes:customer_offer", args=[selected.pk])
        response = self.client.get(url)
        self.assertEqual(response.context["form"].initial["phone_2"], "222")
        self.assertNotContains(response, 'id="restore-draft"')
        self.client.post(url, self.data(first_name="", last_name="", email="shared@example.com", phone_1="", phone_2="222"))
        self.assertEqual(Quote.objects.get().customer_id, selected.pk)
        self.assertEqual(Customer.objects.count(), 2)

    def test_admin_customer_without_name_has_link_and_offer_action(self):
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        customer = Customer.objects.create(email="nameless@example.com")
        url = reverse("quotes:customer_offer", args=[customer.pk])
        response = self.client.get(reverse("admin:customers_customer_changelist"))
        self.assertContains(response, "nameless@example.com")
        self.assertContains(response, url)
        self.assertContains(response, "customers/customer_rows.js")
        response = self.client.get(reverse("admin:customers_customer_change", args=[customer.pk]))
        self.assertContains(response, url)

    def test_logged_out_user_is_sent_to_admin_login(self):
        self.client.logout()
        response = self.client.get(reverse("quotes:new_inquiry"))
        self.assertRedirects(
            response,
            f"/admin/login/?next={reverse('quotes:new_inquiry')}",
            fetch_redirect_response=False,
        )

    def test_return_cannot_be_before_pickup(self):
        response = self.client.post(
            reverse("quotes:new_inquiry"),
            self.data(return_date=(self.pickup - timedelta(days=1)).strftime("%d-%m-%Y")),
        )
        self.assertContains(response, "Возврат должен быть позже получения.")
        self.assertEqual(Quote.objects.count(), 0)

    def test_form_offers_city_and_service_separately(self):
        response = self.client.get(reverse("quotes:new_inquiry"))
        self.assertContains(response, 'data-location-zone="pickup"')
        self.assertContains(response, 'data-location-zone="return"')
        self.assertContains(response, "Получение")
        self.assertContains(response, "Возврат")
        self.assertContains(response, "Город получения")
        self.assertContains(response, "Доставка по адресу клиента")
        self.assertContains(response, "Другой город / страна")
        choices = list(response.context["form"].fields["pickup_city"].choices)
        self.assertEqual(choices[:2], [("", "Выберите город"), ("OTHER", "Другой город / страна")])

    def test_other_pickup_and_return_city_are_saved_with_country(self):
        response = self.client.post(reverse("quotes:new_inquiry"), self.data(
            pickup_city="OTHER", pickup_other_country="Germany", pickup_other_city="Berlin",
            return_city="OTHER", return_other_country="Austria", return_other_city="Vienna",
        ))
        self.assertEqual(response.status_code, 302)
        quote = Quote.objects.get()
        self.assertEqual(quote.pickup_city, "Berlin, Germany")
        self.assertEqual(quote.return_city, "Vienna, Austria")

    def test_manual_adjustment_is_added_to_one_offer_option(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data(extra_choices=[]))
        quote = Quote.objects.get()
        group = self.form_groups[0]
        response = self.client.post(reverse("quotes:calculate_quote", args=[quote.quote_number]), {
            "selected_options": [group.pk],
            f"manual_label_{group.pk}": "Delivery to Vienna",
            f"manual_amount_{group.pk}": "125.50",
        })
        self.assertEqual(response.status_code, 302)
        option = quote.options.get(vehicle_group=group)
        self.assertEqual(option.manual_adjustment_label, "Delivery to Vienna")
        self.assertEqual(option.manual_adjustment_amount, Decimal("125.50"))
        self.assertEqual(option.total_price_gross, Decimal("525.50"))

    def test_form_offers_real_supplier_vehicle_groups(self):
        response = self.client.get(reverse("quotes:new_inquiry"))
        for group in self.form_groups:
            self.assertContains(response, group.group_code)
            self.assertContains(response, group.group_name)

    def test_new_form_does_not_preselect_unrelated_suppliers(self):
        from .forms import FirstInquiryForm

        form = FirstInquiryForm()
        self.assertIsNone(form.fields["suppliers"].initial)
        response = self.client.get(reverse("quotes:new_inquiry"))
        self.assertContains(response, f'data-supplier-id="{self.supplier.pk}"')

    def test_group_without_any_price_is_not_offered(self):
        from .forms import FirstInquiryForm, vehicle_group_section

        group = VehicleGroup.objects.create(
            supplier=self.supplier, group_code="FVMR", group_name="R",
            transmission=VehicleGroup.Transmission.MANUAL,
        )
        self.assertEqual(vehicle_group_section(group), "NINE_SEAT")
        widget = FirstInquiryForm().fields["vehicle_groups"].widget
        sections = widget.get_context("vehicle_groups", [], {})["widget"]["sections"]
        matching = [section["name"] for section in sections
                    for _, options in section["columns"] for option in options
                    if str(option["value"]) == str(group.pk)]
        self.assertEqual(matching, [])

    def test_vehicle_picker_groups_suppliers_without_repeating_names_in_labels(self):
        from .forms import FirstInquiryForm

        other = Supplier.objects.create(supplier_code="DESIGN", supplier_name="Another supplier")
        group = VehicleGroup.objects.create(supplier=other, group_code="B_AUTO", group_name="Compact automatic", rate_source_group=self.form_groups[0])
        group.comparison_classes.add(self.form_groups[0].comparison_classes.first())
        form = FirstInquiryForm(initial={"vehicle_groups": [group.pk]})
        widget = form.fields["vehicle_groups"].widget
        context = widget.get_context("vehicle_groups", [str(group.pk)], {"id": "id_vehicle_groups"})
        options = [option for section in context["widget"]["sections"] for _, column in section["columns"] for option in column]
        self.assertEqual(len(options), len(set(str(option["value"]) for option in options)))
        for option in options:
            self.assertNotIn("supplier", str(option["label"]))
        selected = [option for option in options if option["selected"]]
        self.assertEqual([str(option["value"]) for option in selected], [str(group.pk)])
        html = str(form["vehicle_groups"])
        self.assertIn('<h4>Another supplier</h4>', html)
        self.assertIn('name="vehicle_groups"', html)
        self.assertIn('checked', html)

    def test_vehicle_selection_survives_form_validation_error(self):
        response = self.client.post(reverse("quotes:new_inquiry"), self.data(pickup_date=""))
        form = response.context["form"]
        self.assertEqual(set(form["vehicle_groups"].value()), {str(group.pk) for group in self.form_groups})
        self.assertContains(response, 'checked')

    def test_admin_loads_compact_styles(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "quotes/admin_compact.css")

    def test_customer_lookup_returns_history_and_warning(self):
        customer = Customer.objects.create(
            first_name="Old", last_name="Client", email="old@example.com",
            phone_1="123", warning_level=Customer.WarningLevel.WARNING,
            warning_text="Check previous cancellation",
        )
        response = self.client.get(
            reverse("quotes:customer_lookup"), {"email": "OLD@example.com"}
        )
        data = response.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["id"], customer.id)
        self.assertEqual(data["warning_code"], "WARNING")
        self.assertEqual(data["quote_count"], 0)

    def test_customer_lookup_marks_unknown_contact_as_new(self):
        response = self.client.get(
            reverse("quotes:customer_lookup"), {"email": "new@example.com"}
        )
        self.assertEqual(response.json(), {"found": False})

    def test_selected_quote_option_keeps_price_snapshot(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        comparison = VehicleComparisonClass.objects.first()
        group = VehicleGroup.objects.create(
            supplier=self.supplier, group_code="TEST-GROUP", group_name="Test group"
        )
        option = QuoteOption.objects.create(
            quote=quote,
            supplier=self.supplier,
            vehicle_group=group,
            comparison_class=comparison,
            supplier_name_snapshot=self.supplier.supplier_name,
            vehicle_group_name_snapshot=group.group_name,
            total_price_gross=Decimal("1234.00"),
            calculation_snapshot={"daily_rate": "300.00", "days": 4},
        )
        self.assertEqual(option.total_price_gross, Decimal("1234.00"))
        self.assertEqual(option.calculation_snapshot["days"], 4)

    def _add_included_option(self, quote):
        comparison = VehicleComparisonClass.objects.first()
        group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code=f"SEND-{quote.pk}",
            group_name="Send test group",
        )
        return QuoteOption.objects.create(
            quote=quote,
            supplier=self.supplier,
            vehicle_group=group,
            comparison_class=comparison,
            supplier_name_snapshot=self.supplier.supplier_name,
            vehicle_group_name_snapshot=group.group_name,
            total_price_gross=Decimal("1234.00"),
            calculation_snapshot={
                "days": 4,
                "hebrew_vehicle_class": "Test vehicle",
                "included_items": [],
                "excluded_items": [],
            },
            is_included=True,
        )

    def test_offer_shows_body_and_transmission_from_vehicle_group(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        option = self._add_included_option(quote)
        group = option.vehicle_group
        group.body_type = VehicleGroup.BodyType.ESTATE
        group.transmission = VehicleGroup.Transmission.MANUAL
        group.save(update_fields=["body_type", "transmission"])

        response = self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number]))
        self.assertContains(response, group.get_body_type_display())
        self.assertContains(response, group.get_transmission_display())
        option.refresh_from_db()
        self.assertEqual(option.calculation_snapshot["body_type_label"], group.get_body_type_display())
        self.assertEqual(option.calculation_snapshot["transmission_label"], group.get_transmission_display())

        copied = self.client.get(reverse("quotes:copy_quote", args=[quote.quote_number])).json()
        self.assertIn(group.get_body_type_display(), copied["text"])
        self.assertIn(group.get_transmission_display(), copied["text"])

    def test_offer_does_not_invent_missing_body_type(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        option = self._add_included_option(quote)
        option.vehicle_group.transmission = VehicleGroup.Transmission.AUTOMATIC
        option.vehicle_group.save(update_fields=["transmission"])
        response = self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number]))
        self.assertContains(response, option.vehicle_group.get_transmission_display())
        option.refresh_from_db()
        self.assertEqual(option.calculation_snapshot["body_type_label"], "")

    def test_offer_reads_fuel_description_from_group_data(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        option = self._add_included_option(quote)
        group = option.vehicle_group
        group.fuel_type_note = "TEST-FUEL-HE"
        group.save(update_fields=["fuel_type_note"])

        response = self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number]))
        self.assertContains(response, "TEST-FUEL-HE")
        option.refresh_from_db()
        self.assertEqual(option.calculation_snapshot["fuel_type_label"], "TEST-FUEL-HE")
        copied = self.client.get(reverse("quotes:copy_quote", args=[quote.quote_number])).json()
        self.assertIn("TEST-FUEL-HE", copied["text"])

    def test_mixed_sedan_hatchback_group_does_not_promise_either_body(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        option = self._add_included_option(quote)
        group = option.vehicle_group
        group.body_type = VehicleGroup.BodyType.HATCHBACK
        group.transmission = VehicleGroup.Transmission.AUTOMATIC
        group.save(update_fields=["body_type", "transmission"])
        sedan, _ = VehicleComparisonClass.objects.get_or_create(
            code="C_AUTO_SEDAN", defaults={"name": "Test sedan"}
        )
        hatch, _ = VehicleComparisonClass.objects.get_or_create(
            code="C_AUTO_HATCH", defaults={"name": "Test hatchback"}
        )
        group.comparison_classes.add(sedan, hatch)
        option.comparison_class = sedan
        option.save(update_fields=["comparison_class"])

        self.assertEqual(vehicle_class_presentation(sedan, group), ("קבוצה C", ""))
        response = self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number]))
        self.assertContains(response, "קבוצה C")
        option.refresh_from_db()
        self.assertEqual(option.calculation_snapshot["body_type_label"], "")
        self.assertEqual(option.calculation_snapshot["transmission_label"], "Automatic")

    def test_copy_offer_returns_formatted_content_without_sending(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self._add_included_option(quote)
        response = self.client.get(reverse("quotes:copy_quote", args=[quote.quote_number]))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertIn('dir="rtl"', content["html"])
        self.assertIn("1234", content["html"])
        self.assertNotIn("Выслать оферту клиенту", content["html"])
        self.assertNotIn("Скопировать оферту", content["html"])
        self.assertNotIn("<script", content["html"])
        self.assertTrue(content["text"])
        self.assertEqual(len(mail.outbox), 0)
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertIsNone(quote.sent_at)
        self.assertFalse(quote.email_deliveries.exists())

    def test_copy_offer_requires_login_and_selected_options(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        url = reverse("quotes:copy_quote", args=[quote.quote_number])
        self.assertEqual(self.client.get(url).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    @override_settings(MAILERS={
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    })
    def test_send_quote_emails_offer_and_saves_exact_snapshot(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self._add_included_option(quote)

        response = self.client.post(
            reverse("quotes:send_quote", args=[quote.quote_number])
        )

        self.assertRedirects(
            response, reverse("quotes:quote_preview", args=[quote.quote_number])
        )
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.SENT)
        self.assertEqual(quote.sent_by_user, self.user)
        self.assertEqual(quote.email_deliveries.get().sent_by_user, self.user)
        self.assertIsNotNone(quote.sent_at)
        self.assertEqual(quote.sent_to_email, "anna@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["anna@example.com"])
        self.assertEqual(quote.sent_subject, mail.outbox[0].subject)
        self.assertEqual(quote.sent_html_snapshot, mail.outbox[0].alternatives[0].content)
        self.assertNotIn("Выслать оферту клиенту", quote.sent_html_snapshot)
        self.assertIn('dir="rtl"', quote.sent_html_snapshot)
        self.assertIn('max-width:760px', quote.sent_html_snapshot)
        self.assertIn('text-align:right', quote.sent_html_snapshot)
        self.assertIn("ההצעה הזו הוכנה בעזרת בינה מלאכותית", quote.sent_html_snapshot)
        for benefit in STANDARD_INCLUDED_ITEMS:
            self.assertEqual(quote.sent_html_snapshot.count(f"<li>{benefit}</li>"), 1)

    @override_settings(MAILERS={
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    })
    def test_resending_offer_uses_new_subject_and_keeps_complete_content(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self._add_included_option(quote)
        url = reverse("quotes:send_quote", args=[quote.quote_number])

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(len(mail.outbox), 2)
        first, second = mail.outbox
        self.assertNotEqual(first.subject, second.subject)
        for message in mail.outbox:
            self.assertIn(quote.quote_number, message.subject)
            self.assertIn("Version", message.subject)
            for benefit in STANDARD_INCLUDED_ITEMS:
                self.assertIn(benefit, message.alternatives[0].content)
        self.assertEqual(first.alternatives[0].content, second.alternatives[0].content)
        quote.refresh_from_db()
        self.assertEqual(quote.sent_subject, second.subject)

    @override_settings(MAILERS={
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    })
    def test_send_quote_is_blocked_without_valid_customer_email(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self._add_included_option(quote)
        Customer.objects.filter(pk=quote.customer_id).update(email="wrong-address")

        response = self.client.post(
            reverse("quotes:send_quote", args=[quote.quote_number]), follow=True
        )

        quote.refresh_from_db()
        self.assertContains(response, "у клиента нет правильного email")
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(MAILERS={
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    })
    def test_send_quote_is_blocked_without_included_options(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()

        response = self.client.post(
            reverse("quotes:send_quote", args=[quote.quote_number]), follow=True
        )

        quote.refresh_from_db()
        self.assertContains(response, "сначала выберите хотя бы один вариант")
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(len(mail.outbox), 0)

    def test_quote_preview_has_send_button(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self._add_included_option(quote)

        response = self.client.get(
            reverse("quotes:quote_preview", args=[quote.quote_number])
        )

        self.assertContains(response, "Выслать из системы")
        self.assertNotContains(response, "Дополнительно: отправка из системы")
        self.assertContains(response, quote.customer.email)
        self.assertContains(
            response, reverse("quotes:send_quote", args=[quote.quote_number])
        )

    def test_calculation_steps_are_real_navigation_links(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        response = self.client.get(
            reverse("quotes:calculate_quote", args=[quote.quote_number])
        )
        self.assertContains(
            response, f"/admin/customers/customer/{quote.customer_id}/change/"
        )
        self.assertContains(
            response, reverse("quotes:inquiry_saved", args=[quote.quote_number])
        )
        self.assertContains(
            response, reverse("quotes:quote_preview", args=[quote.quote_number])
        )
        self.assertContains(response, "Сначала клиент должен выбрать вариант")

    def test_groups_without_any_price_are_hidden_before_offer_creation(self):
        VehicleRate.objects.all().delete()
        response = self.client.get(reverse("quotes:new_inquiry"))
        for group in self.form_groups:
            self.assertNotContains(response, group.group_code)

    def test_calculation_does_not_show_selected_groups_without_a_matching_rate(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        VehicleRate.objects.all().delete()

        response = self.client.get(
            reverse("quotes:calculate_quote", args=[quote.quote_number])
        )

        self.assertNotContains(response, "Варианты без цены")
        self.assertNotContains(response, "Нельзя рассчитать")

    def test_selected_supplier_gets_matching_class_when_no_group_was_checked(self):
        from suppliers.models import PriceDayRange, PriceList, PriceSeason, VehicleRate

        other = Supplier.objects.create(supplier_code="03", supplier_name="Test third supplier")
        comparison = self.form_groups[0].comparison_classes.first()
        matching = VehicleGroup.objects.create(
            supplier=other, group_code="MATCH", group_name="Matching class"
        )
        matching.comparison_classes.add(comparison)
        unrelated = VehicleGroup.objects.create(
            supplier=other, group_code="OTHER", group_name="Other class"
        )
        unrelated.comparison_classes.add(self.form_groups[1].comparison_classes.first())
        pickup_date = timezone.localtime(self.pickup).date()
        price_list = PriceList.objects.create(
            supplier=other, name="Test rates", version="test-v1",
            effective_from=pickup_date, status="ACTIVE",
        )
        season = PriceSeason.objects.create(
            price_list=price_list, season_code="TEST", season_name="Test season",
            rental_date_from=pickup_date,
        )
        day_range = PriceDayRange.objects.create(
            price_list=price_list, range_code="TEST", label="Test days", days_from=1,
        )
        VehicleRate.objects.create(
            season=season, day_range=day_range, vehicle_group=matching,
            daily_rate_gross=100,
        )
        self.client.post(reverse("quotes:new_inquiry"), self.data(
            suppliers=[str(self.supplier.pk), str(other.pk)],
            vehicle_groups=[str(self.form_groups[0].pk)],
        ))
        options = calculate_quote_options(Quote.objects.get())
        self.assertTrue(any(item["group"] == matching and item["available"] for item in options))
        self.assertFalse(any(item["group"] == unrelated for item in options))

    def test_supplier_without_matching_class_is_skipped_with_visible_warning(self):
        other = Supplier.objects.create(supplier_code="NO_MATCH", supplier_name="No match supplier")
        response = self.client.post(reverse("quotes:new_inquiry"), self.data(
            suppliers=[str(self.supplier.pk), str(other.pk)],
            vehicle_groups=[str(self.form_groups[0].pk)],
        ))
        quote = Quote.objects.get()
        self.assertRedirects(response, reverse("quotes:inquiry_saved", args=[quote.quote_number]), fetch_redirect_response=False)
        self.assertNotIn(other, quote.requested_suppliers.all())
        self.assertContains(self.client.get(response.url), "No match supplier")

    def test_imported_form_with_old_supplier_defaults_reaches_calculation(self):
        other = Supplier.objects.create(supplier_code="NO_MATCH", supplier_name="No match supplier")
        response = self.client.post(reverse("quotes:new_inquiry"), self.data(
            suppliers=[str(self.supplier.pk), str(other.pk)],
            vehicle_groups=[str(self.form_groups[0].pk)],
            imported_inquiry="1",
        ))
        quote = Quote.objects.get()
        self.assertRedirects(response, reverse("quotes:calculate_quote", args=[quote.quote_number]), fetch_redirect_response=False)
        self.assertContains(self.client.get(response.url), "No match supplier")

    def test_quote_gets_editable_snapshot_of_template_blocks(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        self.assertTrue(QuoteTemplate.objects.filter(language="Hebrew").exists())
        ensure_quote_document_blocks(quote)
        first_block = quote.document_blocks.first()
        original_content = first_block.content
        template_block = first_block.source_block
        template_block.content = "Changed base template"
        template_block.save(update_fields=["content"])
        first_block.refresh_from_db()
        self.assertEqual(first_block.content, original_content)

    def test_existing_draft_gets_editable_ai_note(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        ensure_quote_document_blocks(quote)
        quote.document_blocks.filter(block_key="AI_NOTE").delete()
        ensure_quote_document_blocks(quote)
        note = quote.document_blocks.get(block_key="AI_NOTE")
        self.assertTrue(note.is_enabled)
        self.assertIn("ההצעה הזו הוכנה בעזרת בינה מלאכותית", note.content)
        self.assertContains(
            self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number])),
            note.content,
        )

    def test_customer_offer_uses_hebrew_vehicle_class_name(self):
        self.assertEqual(
            HEBREW_VEHICLE_CLASS_NAMES["SUV_BIG_AUTO"],
            "SUV גדול — אוטומטי",
        )

    def test_supplier_specific_class_name_comes_from_data(self):
        comparison = VehicleComparisonClass.objects.create(
            code="TEST-CUSTOM-CLASS", name="TEST-NAME-HE"
        )
        group = self.form_groups[0]
        self.assertEqual(vehicle_class_presentation(comparison, group)[0], "TEST-NAME-HE")

    def test_standard_benefits_replace_legacy_wording_and_keep_selected_extras(self):
        items = normalize_included_items([
            "עד שני נהגים", "חבילת With Comfort Package",
            "ביטוח מלא עם ביטול השתתפות - SCDW", "ללא הגבלת ק״מ",
            "כיסא תינוק / בוסטר × 1", "נהג נוסף × 1",
            *STANDARD_INCLUDED_ITEMS,
        ])
        for benefit in STANDARD_INCLUDED_ITEMS:
            self.assertEqual(items.count(benefit), 1)
        self.assertIn("כיסא תינוק / בוסטר × 1", items)
        self.assertIn("נהג נוסף × 1", items)
        self.assertNotIn("עד שני נהגים", items)
        self.assertNotIn("ביטוח מלא עם ביטול השתתפות - SCDW", items)

    def test_every_supplier_option_shows_standard_benefits_in_preview(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        for code in ("01", "02", "03"):
            supplier, _ = Supplier.objects.get_or_create(
                supplier_code=code, defaults={"supplier_name": f"Supplier {code}"},
            )
            self.supplier = supplier
            self._add_included_option(quote)
        response = self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number]))
        for benefit in STANDARD_INCLUDED_ITEMS:
            self.assertContains(response, f"<li>{benefit}</li>", count=3)

    def test_customer_offer_translates_mandatory_service_fees(self):
        self.assertEqual(
            HEBREW_EXTRA_NAMES["AIRPORT_FEE"],
            "תוספת שירות בשדה התעופה",
        )
        self.assertEqual(
            HEBREW_EXTRA_NAMES["CITY_ADDRESS_DELIVERY"],
            "מסירה או החזרה בכתובת בעיר",
        )

    def test_extra_rate_description_shows_daily_price_in_hebrew(self):
        from types import SimpleNamespace

        rate = SimpleNamespace(
            formula_config={},
            calculation_type="PER_DAY",
            amount_gross=Decimal("20.00"),
            maximum_amount_gross=None,
        )
        self.assertEqual(_rate_description(rate), "20.00 PLN ליום")

    def test_daily_extra_applies_maximum_to_each_selected_item(self):
        from types import SimpleNamespace

        rate = SimpleNamespace(
            formula_config={},
            calculation_type="PER_DAY",
            amount_gross=Decimal("20.00"),
            minimum_amount_gross=None,
            maximum_amount_gross=Decimal("150.00"),
        )

        self.assertEqual(
            _extra_price(rate, days=Decimal("5"), quantity=Decimal("2")),
            Decimal("200.00"),
        )
        self.assertEqual(
            _extra_price(rate, days=Decimal("20"), quantity=Decimal("2")),
            Decimal("300.00"),
        )

    def test_child_seat_name_in_offer_includes_quantity(self):
        from types import SimpleNamespace

        extra = SimpleNamespace(
            extra_code="CHILD_SEAT",
            name="Child seat",
        )

        self.assertEqual(
            _extra_line_name(extra, Decimal("3")),
            f'{HEBREW_EXTRA_NAMES["CHILD_SEAT"]} × 3',
        )

    def test_luggage_information_is_shown_only_when_supplier_provided_it(self):
        from types import SimpleNamespace

        known = SimpleNamespace(
            luggage_volume_liters=460,
            luggage_large=None,
            luggage_small=None,
            cargo_note="",
        )
        unknown = SimpleNamespace(
            luggage_volume_liters=None,
            luggage_large=None,
            luggage_small=None,
            cargo_note="",
        )

        self.assertIn("460", _luggage_info(known))
        self.assertEqual(_luggage_info(unknown), "")

    def test_old_option_gets_standard_benefits_without_changing_price_or_days(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        comparison = VehicleComparisonClass.objects.first()
        group = VehicleGroup.objects.create(
            supplier=self.supplier, group_code="OLD", group_name="Old group"
        )
        option = QuoteOption.objects.create(
            quote=quote,
            supplier=self.supplier,
            vehicle_group=group,
            comparison_class=comparison,
            supplier_name_snapshot=self.supplier.supplier_name,
            vehicle_group_name_snapshot=group.group_name,
            total_price_gross=Decimal("100.00"),
            calculation_snapshot={"days": 4},
            is_included=True,
        )
        ensure_quote_option_presentation(quote)
        option.refresh_from_db()
        self.assertEqual(option.calculation_snapshot["days"], 4)
        self.assertEqual(option.total_price_gross, Decimal("100.00"))
        for benefit in STANDARD_INCLUDED_ITEMS:
            self.assertIn(benefit, option.calculation_snapshot["included_items"])

    def test_hebrew_preview_does_not_use_russian_location_labels(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        response = self.client.get(
            reverse("quotes:quote_preview", args=[quote.quote_number])
        )
        self.assertContains(response, "שדה התעופה")
        self.assertNotContains(response, "Аэропорт")
        self.assertNotContains(response, "Доставка по адресу клиента")
        self.assertIn("no-cache", response.headers["Cache-Control"])

    def test_airport_pickup_method_appears_in_preview_and_copy(self):
        from suppliers.models import AirportPickupWording, SupplierLocation

        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        SupplierLocation.objects.create(
            supplier=self.supplier, location_code="KRK", location_name="Airport",
            city="Kraków", location_type="AIRPORT", airport_code="KRK",
            has_rental_desk=True,
        )
        group = self.form_groups[0]
        QuoteOption.objects.create(
            quote=quote, supplier=self.supplier, vehicle_group=group,
            comparison_class=group.comparison_classes.first(),
            supplier_name_snapshot=self.supplier.supplier_name,
            vehicle_group_name_snapshot=group.group_name,
            total_price_gross=Decimal("100.00"), is_included=True,
        )
        expected = AirportPickupWording.objects.get(method_code="DESK").text_he
        preview = self.client.get(reverse("quotes:quote_preview", args=[quote.quote_number]))
        copied = self.client.get(reverse("quotes:copy_quote", args=[quote.quote_number]))
        self.assertContains(preview, expected)
        self.assertIn(expected, copied.json()["text"])

    def test_new_preview_address_uses_the_same_updated_template(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        response = self.client.get(
            reverse("quotes:quote_preview_v2", args=[quote.quote_number])
        )
        self.assertContains(response, "price-row")
        self.assertNotContains(response, "המחיר כולל מע״מ ואת השירותים שנבחרו")

    def test_preview_has_top_navigation_to_previous_steps(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        response = self.client.get(
            reverse("quotes:quote_preview", args=[quote.quote_number])
        )
        self.assertContains(response, 'class="workflow"')
        self.assertContains(
            response, reverse("quotes:calculate_quote", args=[quote.quote_number])
        )
        self.assertContains(
            response, reverse("quotes:inquiry_saved", args=[quote.quote_number])
        )

    def test_editing_quote_changes_same_quote_and_clears_old_document(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        ensure_quote_document_blocks(quote)
        self.assertTrue(quote.document_blocks.exists())
        response = self.client.post(
            reverse("quotes:edit_quote", args=[quote.quote_number]),
            self.data(
                return_date=(self.pickup + timedelta(days=6)).strftime("%d-%m-%Y"),
                return_time="14:00",
            ),
        )
        quote.refresh_from_db()
        self.assertRedirects(
            response, reverse("quotes:calculate_quote", args=[quote.quote_number])
        )
        self.assertEqual(Quote.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(quote.rental_days, 6)
        self.assertTrue(quote.document_blocks.exists())

    def test_duplicate_creates_new_quote_for_same_customer_without_prices(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        source = Quote.objects.get()
        response = self.client.post(
            reverse("quotes:duplicate_quote", args=[source.quote_number])
        )
        duplicate = Quote.objects.exclude(pk=source.pk).get()
        self.assertRedirects(
            response, reverse("quotes:edit_quote", args=[duplicate.quote_number])
        )
        self.assertEqual(Quote.objects.count(), 2)
        self.assertEqual(duplicate.customer, source.customer)
        self.assertNotEqual(duplicate.quote_number, source.quote_number)
        self.assertFalse(duplicate.options.exists())
        self.assertFalse(duplicate.document_blocks.exists())

    def test_offer_option_displays_its_own_deposit(self):
        self.client.post(reverse("quotes:new_inquiry"), self.data())
        quote = Quote.objects.get()
        comparison = VehicleComparisonClass.objects.first()
        group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="DEPOSIT-GROUP",
            group_name="Deposit group",
            deposit_amount=Decimal("500.00"),
        )
        QuoteOption.objects.create(
            quote=quote,
            supplier=self.supplier,
            vehicle_group=group,
            comparison_class=comparison,
            supplier_name_snapshot=self.supplier.supplier_name,
            vehicle_group_name_snapshot=group.group_name,
            total_price_gross=Decimal("1000.00"),
            deposit_amount=Decimal("500.00"),
            deposit_currency="PLN",
            calculation_snapshot={
                "hebrew_vehicle_class": "SUV גדול — אוטומטי",
                "included_items": [],
                "excluded_items": [],
            },
            is_included=True,
        )
        response = self.client.get(
            reverse("quotes:quote_preview", args=[quote.quote_number])
        )
        self.assertContains(response, "פיקדון:")
        self.assertContains(response, "500.00 PLN")

    def test_removed_generic_deposit_sentence_is_not_in_template(self):
        sentence = "אין להסתמך על סכום פיקדון אחיד לכל החברות או לכל קבוצות הרכב."
        self.assertFalse(
            QuoteTemplate.objects.filter(blocks__content__contains=sentence).exists()
        )

    def test_kaizen_cross_border_offer_uses_selected_rate(self):
        from types import SimpleNamespace

        extra = SimpleNamespace(
            supplier=SimpleNamespace(supplier_code="01"),
            extra_code="CROSS_BORDER",
        )
        old_rate = SimpleNamespace(
            formula_config={}, calculation_type="PER_RENTAL",
            amount_gross=Decimal("299.00"),
        )
        self.assertEqual(
            _quoted_extra_price(extra, old_rate, Decimal("5")),
            Decimal("299.00"),
        )
