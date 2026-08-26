from django.contrib import admin
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Supplier, SupplierLocation


class SupplierTests(TestCase):
    def test_new_supplier_is_active_and_uses_pln_by_default(self):
        supplier = Supplier.objects.create(
            supplier_code="KAIZEN",
            supplier_name="Kaizen Rent",
        )

        self.assertEqual(supplier.status, Supplier.Status.ACTIVE)
        self.assertEqual(supplier.default_currency, "PLN")

    def test_supplier_is_displayed_by_its_name(self):
        supplier = Supplier(
            supplier_code="ONE",
            supplier_name="One Rent",
        )

        self.assertEqual(str(supplier), "One Rent")

    def test_supplier_is_available_in_admin(self):
        self.assertIn(Supplier, admin.site._registry)


class SupplierLocationTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="KAIZEN",
            supplier_name="Kaizen Rent",
        )

    def test_location_has_safe_defaults(self):
        location = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="KRK",
            location_name="Krakow Airport",
            city="Krakow",
        )

        self.assertEqual(location.country, "Poland")
        self.assertTrue(location.supports_pickup)
        self.assertTrue(location.supports_return)
        self.assertTrue(location.is_active)
        self.assertFalse(location.has_rental_desk)
        self.assertFalse(location.supports_terminal_delivery)
        self.assertFalse(location.supports_address_delivery)

    def test_location_can_record_each_service_method(self):
        location = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="WAW",
            location_name="Warsaw Airport",
            city="Warsaw",
            has_rental_desk=True,
            supports_terminal_delivery=True,
            supports_address_delivery=True,
        )

        self.assertTrue(location.has_rental_desk)
        self.assertTrue(location.supports_terminal_delivery)
        self.assertTrue(location.supports_address_delivery)

    def test_same_location_code_can_be_used_by_different_suppliers(self):
        other_supplier = Supplier.objects.create(
            supplier_code="ONE",
            supplier_name="One Rent",
        )
        SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="KRK",
            location_name="Krakow Airport",
            city="Krakow",
        )

        second_location = SupplierLocation.objects.create(
            supplier=other_supplier,
            location_code="KRK",
            location_name="Krakow Airport",
            city="Krakow",
        )

        self.assertEqual(second_location.location_code, "KRK")

    def test_location_code_cannot_repeat_for_same_supplier(self):
        SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="KRK",
            location_name="Krakow Airport",
            city="Krakow",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierLocation.objects.create(
                supplier=self.supplier,
                location_code="KRK",
                location_name="Krakow City",
                city="Krakow",
            )

    def test_location_display_includes_supplier_name(self):
        location = SupplierLocation(
            supplier=self.supplier,
            location_code="KRK",
            location_name="Krakow Airport",
            city="Krakow",
        )

        self.assertEqual(str(location), "Kaizen Rent — Krakow Airport")

    def test_location_is_available_in_admin(self):
        self.assertIn(SupplierLocation, admin.site._registry)
