from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import TaxRate


class TaxRateTests(TestCase):
    def test_new_tax_rate_is_active_by_default(self):
        tax_rate = TaxRate.objects.create(
            country="Poland",
            tax_name="VAT",
            rate_percent=Decimal("23.00"),
            valid_from=date(2011, 1, 1),
        )

        self.assertTrue(tax_rate.is_active)

    def test_tax_rate_is_displayed_with_country_name_and_percent(self):
        tax_rate = TaxRate(
            country="Poland",
            tax_name="VAT",
            rate_percent=Decimal("23.00"),
            valid_from=date(2011, 1, 1),
        )

        self.assertEqual(str(tax_rate), "Poland VAT 23.00%")

    def test_rate_above_one_hundred_is_rejected(self):
        tax_rate = TaxRate(
            country="Poland",
            rate_percent=Decimal("101.00"),
            valid_from=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError):
            tax_rate.full_clean()

    def test_end_date_before_start_date_is_rejected(self):
        tax_rate = TaxRate(
            country="Poland",
            rate_percent=Decimal("23.00"),
            valid_from=date(2026, 1, 1),
            valid_to=date(2025, 12, 31),
        )

        with self.assertRaises(ValidationError):
            tax_rate.full_clean()

    def test_tax_rate_is_available_in_admin(self):
        self.assertIn(TaxRate, admin.site._registry)
