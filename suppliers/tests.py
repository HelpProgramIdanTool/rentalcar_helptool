from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from openpyxl import Workbook

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
        self.assertFalse(location.supports_self_return_via_key_box)

    def test_location_can_record_each_service_method(self):
        location = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="WAW",
            location_name="Warsaw Airport",
            city="Warsaw",
            has_rental_desk=True,
            supports_terminal_delivery=True,
            supports_address_delivery=True,
            supports_self_return_via_key_box=True,
        )

        self.assertTrue(location.has_rental_desk)
        self.assertTrue(location.supports_terminal_delivery)
        self.assertTrue(location.supports_address_delivery)
        self.assertTrue(location.supports_self_return_via_key_box)

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


class CarFreeLocationImportTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="03",
            supplier_name="Car Free",
        )
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.file_path = Path(self.temporary_directory.name) / "carfree.xlsx"

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "CarFree Departments"
        worksheet.append(["City", "Type", "Address"])
        worksheet.append(
            [
                "Kraków Balice",
                "Office at the airport - In Terminal",
                "Airport address, Poland",
            ]
        )
        worksheet.append(["Warszawa", "Office in the city", "First address, Poland"])
        worksheet.append(["Warszawa", "Office in the city", "Second address, Poland"])
        worksheet.append(["City", "Type", "Address"])
        worksheet.append(
            [
                "Pardubice Airport",
                "Meet & Greet",
                "Airport address, Czech Republic",
            ]
        )
        workbook.save(self.file_path)

    def test_preview_does_not_save_locations(self):
        output = StringIO()

        call_command("import_carfree_locations", self.file_path, "--preview", stdout=output)

        self.assertEqual(SupplierLocation.objects.count(), 0)
        self.assertIn("Preview only: 4 locations, nothing saved.", output.getvalue())

    def test_import_maps_location_types_and_service_methods(self):
        call_command("import_carfree_locations", self.file_path, stdout=StringIO())

        airport = SupplierLocation.objects.get(location_code="KRK")
        meet_and_greet = SupplierLocation.objects.get(location_code="PED")
        self.assertEqual(airport.location_type, SupplierLocation.LocationType.AIRPORT)
        self.assertTrue(airport.has_rental_desk)
        self.assertEqual(airport.airport_code, "KRK")
        self.assertFalse(meet_and_greet.has_rental_desk)
        self.assertTrue(meet_and_greet.supports_terminal_delivery)
        self.assertEqual(meet_and_greet.country, "Czech Republic")

    def test_import_generates_unique_codes_for_two_city_offices(self):
        call_command("import_carfree_locations", self.file_path, stdout=StringIO())

        self.assertTrue(
            SupplierLocation.objects.filter(location_code="WARSZAWA-CITY").exists()
        )
        self.assertTrue(
            SupplierLocation.objects.filter(location_code="WARSZAWA-CITY-2").exists()
        )

    def test_repeated_import_updates_without_duplicates(self):
        call_command("import_carfree_locations", self.file_path, stdout=StringIO())
        call_command("import_carfree_locations", self.file_path, stdout=StringIO())

        self.assertEqual(SupplierLocation.objects.count(), 4)


class AddressDeliveryLocationTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="03",
            supplier_name="Car Free",
        )
        SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="KRK",
            location_name="Kraków Balice",
            city="Kraków Balice",
            location_type=SupplierLocation.LocationType.AIRPORT,
        )
        SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="KRAKOW-BUS",
            location_name="Kraków",
            city="Kraków",
            location_type=SupplierLocation.LocationType.BRANCH,
        )

    def test_preview_does_not_create_virtual_location(self):
        output = StringIO()

        call_command("create_address_delivery_locations", "--preview", stdout=output)

        self.assertEqual(
            SupplierLocation.objects.filter(
                location_type=SupplierLocation.LocationType.ADDRESS_DELIVERY
            ).count(),
            0,
        )
        self.assertIn("Preview only: 1 virtual locations", output.getvalue())

    def test_two_physical_locations_in_one_city_create_one_virtual_location(self):
        call_command("create_address_delivery_locations", stdout=StringIO())

        delivery = SupplierLocation.objects.get(location_code="KRAKOW-DELIVERY")
        self.assertEqual(
            delivery.location_type,
            SupplierLocation.LocationType.ADDRESS_DELIVERY,
        )
        self.assertFalse(delivery.has_rental_desk)
        self.assertTrue(delivery.supports_address_delivery)
        self.assertEqual(delivery.address, "")

    def test_repeated_creation_updates_without_duplicates(self):
        call_command("create_address_delivery_locations", stdout=StringIO())
        call_command("create_address_delivery_locations", stdout=StringIO())

        self.assertEqual(
            SupplierLocation.objects.filter(location_code="KRAKOW-DELIVERY").count(),
            1,
        )
