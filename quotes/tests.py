from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from suppliers.models import Supplier, VehicleComparisonClass, VehicleGroup

from .models import Quote, QuoteOption, QuoteTemplate
from .services import (
    HEBREW_EXTRA_NAMES,
    HEBREW_VEHICLE_CLASS_NAMES,
    KAIZEN_CROSS_BORDER_PRICE,
    KAIZEN_COMFORT_INCLUDED_ITEMS,
    _extra_line_name,
    _extra_price,
    _luggage_info,
    _rate_description,
    _quoted_extra_price,
    _service_extra_requests,
    ensure_quote_document_blocks,
    ensure_quote_option_presentation,
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

        self.assertContains(response, "Очистить и начать новый запрос")
        self.assertContains(response, "Восстановить черновик")
        self.assertContains(response, "Малые автомобили")
        self.assertContains(response, 'class="message-panel"')
        self.assertContains(response, 'class="form-scroll"')
        self.assertContains(response, "body { margin:0;overflow:hidden; }")
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
        self.assertContains(response, "Укажите хотя бы e-mail или первый телефон.")
        self.assertEqual(Quote.objects.count(), 0)

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
        self.assertContains(response, "Город получения")
        self.assertContains(response, "Доставка по адресу клиента")

    def test_form_offers_real_supplier_vehicle_groups(self):
        response = self.client.get(reverse("quotes:new_inquiry"))
        for group in self.form_groups:
            self.assertContains(response, group.group_code)
            self.assertContains(response, group.group_name)

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

    def test_customer_offer_uses_hebrew_vehicle_class_name(self):
        self.assertEqual(
            HEBREW_VEHICLE_CLASS_NAMES["SUV_BIG_AUTO"],
            "SUV גדול — אוטומטי",
        )

    def test_kaizen_uses_idans_scdw_wording(self):
        self.assertIn(
            "ביטוח מלא עם ביטול השתתפות - SCDW",
            KAIZEN_COMFORT_INCLUDED_ITEMS,
        )

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

    def test_old_option_presentation_is_left_unchanged_without_current_rate(self):
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
        self.assertEqual(option.calculation_snapshot, {"days": 4})

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
        self.assertFalse(quote.document_blocks.exists())

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

    def test_kaizen_cross_border_offer_rate_is_499_per_rental(self):
        from types import SimpleNamespace

        extra = SimpleNamespace(
            supplier=SimpleNamespace(supplier_code="01"),
            extra_code="CROSS_BORDER",
        )
        old_rate = SimpleNamespace(
            formula_config={}, calculation_type="PER_RENTAL",
            amount_gross=Decimal("299.00"),
        )
        self.assertEqual(KAIZEN_CROSS_BORDER_PRICE, Decimal("499.00"))
        self.assertEqual(
            _quoted_extra_price(extra, old_rate, Decimal("5")),
            Decimal("499.00"),
        )
