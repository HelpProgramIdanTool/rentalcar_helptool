from io import StringIO
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from openpyxl import Workbook

from .deposit_rules import DEPOSIT_AMOUNTS_PLN, default_deposit_amount

from .models import (
    Supplier,
    SupplierExtra,
    SupplierExtraRate,
    SupplierLocation,
    PriceDayRange,
    PriceList,
    PriceSeason,
    VehicleGroup,
    VehicleComparisonClass,
    VehicleModel,
    VehicleRate,
)


class VehicleComparisonClassTests(TestCase):
    def test_one_customer_class_can_link_equivalent_supplier_groups(self):
        first_supplier = Supplier.objects.create(supplier_code="A", supplier_name="First")
        second_supplier = Supplier.objects.create(supplier_code="B", supplier_name="Second")
        first_group = VehicleGroup.objects.create(
            supplier=first_supplier, group_code="CDAR", group_name="C automatic hatchback"
        )
        second_group = VehicleGroup.objects.create(
            supplier=second_supplier, group_code="C-AUTO", group_name="C automatic hatchback"
        )
        comparison = VehicleComparisonClass.objects.create(
            code="TEST_C_AUTO_HATCH", name="C — хетчбэк, автомат"
        )
        comparison.vehicle_groups.add(first_group, second_group)

        self.assertEqual(comparison.vehicle_groups.count(), 2)
        self.assertEqual(first_group.comparison_classes.get(), comparison)

    def test_catalog_group_can_use_a_broader_tariff_group(self):
        supplier = Supplier.objects.create(supplier_code="CF", supplier_name="Car Free")
        tariff_group = VehicleGroup.objects.create(
            supplier=supplier, group_code="SUV", group_name="SUV tariff"
        )
        catalog_group = VehicleGroup.objects.create(
            supplier=supplier,
            group_code="SUV-BIG",
            group_name="SUV Big",
            rate_source_group=tariff_group,
        )
        self.assertEqual(catalog_group.effective_rate_group, tariff_group)
from .management.commands.import_vehicle_groups import (
    add_record,
    body_type_from_acriss,
    group_name_for_kaizen,
    split_brand_and_model,
    transmission_from_acriss,
)
from .management.commands.import_supplier_extras import (
    car_free_records,
    extra,
    rate,
    one_rent_records,
    upsert_supplier_extras,
)


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
        self.assertEqual(location.phone, "")

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


class OneRentLocationImportTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="02",
            supplier_name="One Rent",
        )

    def test_preview_does_not_save_locations(self):
        output = StringIO()

        call_command("import_one_rent_locations", "--preview", stdout=output)

        self.assertEqual(SupplierLocation.objects.count(), 0)
        self.assertIn("Preview only: 11 locations, nothing saved.", output.getvalue())

    def test_import_separates_krakow_terminal_and_tina_parking(self):
        call_command("import_one_rent_locations", stdout=StringIO())

        terminal = SupplierLocation.objects.get(location_code="KRK-DELIVERY")
        tina = SupplierLocation.objects.get(location_code="KRK-TINA")
        self.assertTrue(terminal.supports_pickup)
        self.assertFalse(terminal.supports_return)
        self.assertTrue(terminal.supports_terminal_delivery)
        self.assertTrue(tina.supports_pickup)
        self.assertTrue(tina.supports_return)
        self.assertTrue(tina.has_rental_desk)
        self.assertTrue(tina.supports_self_return_via_key_box)

    def test_repeated_import_updates_without_duplicates(self):
        call_command("import_one_rent_locations", stdout=StringIO())
        call_command("import_one_rent_locations", stdout=StringIO())

        self.assertEqual(SupplierLocation.objects.count(), 11)


class KaizenLocationImportTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="01",
            supplier_name="Kaizen Rent",
        )

    def test_preview_does_not_save_locations(self):
        output = StringIO()

        call_command("import_kaizen_locations", "--preview", stdout=output)

        self.assertEqual(SupplierLocation.objects.count(), 0)
        self.assertIn("Preview only: 12 locations, nothing saved.", output.getvalue())

    def test_import_maps_desks_meetings_key_boxes_and_phone(self):
        call_command("import_kaizen_locations", stdout=StringIO())

        waw = SupplierLocation.objects.get(location_code="WAW")
        wmi = SupplierLocation.objects.get(location_code="WMI")
        krk = SupplierLocation.objects.get(location_code="KRK-AIRPORT")
        self.assertTrue(waw.has_rental_desk)
        self.assertFalse(wmi.has_rental_desk)
        self.assertTrue(wmi.supports_terminal_delivery)
        self.assertTrue(krk.supports_self_return_via_key_box)
        self.assertEqual(krk.phone, "+48 881 212 968")
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.phone, "+48 76 727 99 99")

    def test_repeated_import_updates_without_duplicates(self):
        call_command("import_kaizen_locations", stdout=StringIO())
        call_command("import_kaizen_locations", stdout=StringIO())

        self.assertEqual(SupplierLocation.objects.count(), 12)


class VehicleGroupTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="01",
            supplier_name="Kaizen Rent",
        )

    def test_vehicle_group_has_safe_defaults(self):
        group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="CDAR",
            group_name="C Automatic Hatchback",
        )

        self.assertEqual(group.transmission, VehicleGroup.Transmission.UNKNOWN)
        self.assertTrue(group.is_active)
        self.assertIsNone(group.seats)

    def test_same_group_code_can_be_used_by_different_suppliers(self):
        other_supplier = Supplier.objects.create(
            supplier_code="02",
            supplier_name="One Rent",
        )
        VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="CDAR",
            group_name="C Automatic Hatchback",
        )

        second_group = VehicleGroup.objects.create(
            supplier=other_supplier,
            group_code="CDAR",
            group_name="C Automatic",
        )

        self.assertEqual(second_group.group_code, "CDAR")

    def test_vehicle_model_belongs_to_group(self):
        group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="CDAR",
            group_name="C Automatic Hatchback",
        )
        model = VehicleModel.objects.create(
            vehicle_group=group,
            brand="Hyundai",
            model="i30",
        )

        self.assertEqual(model.vehicle_group, group)
        self.assertEqual(str(model), "Hyundai i30")

    def test_vehicle_group_and_model_are_available_in_admin(self):
        self.assertIn(VehicleGroup, admin.site._registry)
        self.assertIn(VehicleModel, admin.site._registry)

    def test_vehicle_group_admin_has_editable_luggage_section(self):
        fieldsets = admin.site._registry[VehicleGroup].fieldsets
        luggage_section = next(fields for title, fields in fieldsets if title == "Багажник")

        self.assertIn("luggage_volume_liters", luggage_section["fields"])
        self.assertIn("luggage_large", luggage_section["fields"])
        self.assertIn("luggage_small", luggage_section["fields"])


class SupplierExtraTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="EXTRAS",
            supplier_name="Extras Test Supplier",
        )
        self.extra = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="CHILD_SEAT",
            name="Child seat",
            category="CHILD_EQUIPMENT",
        )

    def test_extra_codes_are_unique_inside_one_supplier(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierExtra.objects.create(
                supplier=self.supplier,
                extra_code="CHILD_SEAT",
                name="Another child seat",
            )

    def test_rate_stores_final_customer_price_including_vat(self):
        rate = SupplierExtraRate.objects.create(
            extra=self.extra,
            rate_code="DAILY",
            calculation_type=SupplierExtraRate.CalculationType.PER_DAY,
            amount_gross=Decimal("25.00"),
            currency="PLN",
            valid_from=date(2026, 1, 1),
        )

        self.assertEqual(rate.amount_gross, Decimal("25.00"))
        self.assertEqual(
            SupplierExtraRate._meta.get_field("amount_gross").help_text,
            "Final customer price including VAT.",
        )

    def test_rate_supports_location_and_rental_day_range(self):
        location = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="WAW",
            location_name="Warsaw",
            city="Warsaw",
        )
        rate = SupplierExtraRate.objects.create(
            extra=self.extra,
            rate_code="RENTAL_1_7",
            location=location,
            calculation_type=SupplierExtraRate.CalculationType.PER_RENTAL,
            amount_gross=Decimal("100.00"),
            days_from=1,
            days_to=7,
            valid_from=date(2026, 1, 1),
        )

        self.assertEqual(rate.location, location)
        self.assertEqual(rate.days_to, 7)

    def test_rate_rejects_location_of_another_supplier(self):
        other_supplier = Supplier.objects.create(
            supplier_code="OTHER-EXTRAS",
            supplier_name="Other Extras Supplier",
        )
        other_location = SupplierLocation.objects.create(
            supplier=other_supplier,
            location_code="KRK",
            location_name="Krakow",
            city="Krakow",
        )
        rate = SupplierExtraRate(
            extra=self.extra,
            rate_code="OTHER_LOCATION",
            location=other_location,
            calculation_type=SupplierExtraRate.CalculationType.FIXED,
            amount_gross=Decimal("50.00"),
            valid_from=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError):
            rate.full_clean()

    def test_extra_and_rate_are_available_in_admin(self):
        self.assertIn(SupplierExtra, admin.site._registry)
        self.assertIn(SupplierExtraRate, admin.site._registry)

    def test_import_updates_existing_extra_and_rate_without_duplicates(self):
        records = [
            extra(
                "TEST_EXTRA",
                "Test extra",
                "TEST",
                "Source extra",
                [
                    rate(
                        20,
                        SupplierExtraRate.CalculationType.PER_DAY,
                        rate_code="DAILY",
                    )
                ],
            )
        ]
        source_values = {"Source extra": "20 PLN per day"}

        upsert_supplier_extras(
            self.supplier,
            records,
            source_values,
            date(2026, 1, 1),
            "test.xlsx",
        )
        upsert_supplier_extras(
            self.supplier,
            records,
            source_values,
            date(2026, 1, 1),
            "test.xlsx",
        )

        self.assertEqual(
            SupplierExtra.objects.filter(
                supplier=self.supplier,
                extra_code="TEST_EXTRA",
            ).count(),
            1,
        )
        self.assertEqual(
            SupplierExtraRate.objects.filter(extra__extra_code="TEST_EXTRA").count(),
            1,
        )

    def test_car_free_cross_border_rate_includes_daily_charge(self):
        cross_border = next(
            item for item in car_free_records() if item["extra_code"] == "CROSS_BORDER"
        )
        cross_border_rate = cross_border["rates"][0]

        self.assertEqual(cross_border_rate["amount_gross"], Decimal("299"))
        self.assertEqual(
            cross_border_rate["formula_config"]["per_rental_day_gross"],
            "30.00",
        )

    def test_car_free_snow_chains_cost_25_daily_with_250_maximum(self):
        snow_chains = next(
            item for item in car_free_records() if item["extra_code"] == "SNOW_CHAINS"
        )
        snow_chains_rate = snow_chains["rates"][0]

        self.assertEqual(snow_chains_rate["amount_gross"], Decimal("25"))
        self.assertEqual(
            snow_chains_rate["calculation_type"],
            SupplierExtraRate.CalculationType.PER_DAY,
        )
        self.assertEqual(
            snow_chains_rate["maximum_amount_gross"], Decimal("250")
        )

    def test_one_rent_delivery_and_return_is_mandatory_two_hundred(self):
        delivery = next(
            item
            for item in one_rent_records()
            if item["extra_code"] == "CITY_AIRPORT_DELIVERY"
        )
        delivery_rate = delivery["rates"][0]

        self.assertTrue(delivery["is_mandatory"])
        self.assertEqual(delivery_rate["amount_gross"], Decimal("200"))
        self.assertEqual(
            delivery_rate["formula_config"]["pickup_gross"],
            "100.00",
        )
        self.assertEqual(
            delivery_rate["formula_config"]["return_gross"],
            "100.00",
        )


class VehicleRateTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_code="RATES",
            supplier_name="Rate Supplier",
        )
        self.group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="CDAR",
            group_name="C Automatic",
        )
        self.price_list = PriceList.objects.create(
            supplier=self.supplier,
            name="2026 customer rates",
            version="2026",
            effective_from=date(2026, 1, 1),
            status=PriceList.Status.ACTIVE,
            source_type=PriceList.SourceType.EXCEL,
        )
        self.season = PriceSeason.objects.create(
            price_list=self.price_list,
            season_code="HIGH",
            season_name="High season",
            rental_date_from=date(2026, 6, 1),
            rental_date_to=date(2026, 8, 31),
        )
        self.day_range = PriceDayRange.objects.create(
            price_list=self.price_list,
            range_code="D3_6",
            label="3-6 days",
            days_from=3,
            days_to=6,
        )

    def test_vehicle_rate_stores_daily_customer_price_including_vat(self):
        vehicle_rate = VehicleRate.objects.create(
            season=self.season,
            vehicle_group=self.group,
            day_range=self.day_range,
            daily_rate_gross=Decimal("145.00"),
        )

        self.assertEqual(vehicle_rate.daily_rate_gross, Decimal("145.00"))
        self.assertEqual(
            VehicleRate._meta.get_field("daily_rate_gross").help_text,
            "Daily customer price including VAT.",
        )

    def test_vehicle_rate_rejects_group_of_another_supplier(self):
        other_supplier = Supplier.objects.create(
            supplier_code="OTHER-RATE",
            supplier_name="Other Rate Supplier",
        )
        other_group = VehicleGroup.objects.create(
            supplier=other_supplier,
            group_code="CDAR",
            group_name="Other C Automatic",
        )
        vehicle_rate = VehicleRate(
            season=self.season,
            vehicle_group=other_group,
            day_range=self.day_range,
            daily_rate_gross=Decimal("145.00"),
        )

        with self.assertRaises(ValidationError):
            vehicle_rate.full_clean()

    def test_price_tables_are_available_in_admin(self):
        self.assertIn(PriceList, admin.site._registry)
        self.assertIn(PriceSeason, admin.site._registry)
        self.assertIn(PriceDayRange, admin.site._registry)
        self.assertIn(VehicleRate, admin.site._registry)


class VehicleGroupImportRuleTests(TestCase):
    def test_automatic_and_manual_transmission_are_read_from_acriss(self):
        self.assertEqual(
            transmission_from_acriss("CDAR"),
            VehicleGroup.Transmission.AUTOMATIC,
        )
        self.assertEqual(
            transmission_from_acriss("CDMR"),
            VehicleGroup.Transmission.MANUAL,
        )

    def test_hatchback_and_sedan_codes_are_separate(self):
        self.assertEqual(
            body_type_from_acriss("CDAR"),
            VehicleGroup.BodyType.HATCHBACK,
        )
        self.assertEqual(
            body_type_from_acriss("CLAR"),
            VehicleGroup.BodyType.SEDAN,
        )
        self.assertNotEqual(
            group_name_for_kaizen("C Aut", "CDAR"),
            group_name_for_kaizen("C Aut", "CLAR"),
        )

    def test_known_brand_is_separated_from_model(self):
        self.assertEqual(
            split_brand_and_model("Toyota Corolla"),
            ("Toyota", "Corolla"),
        )

    def test_models_that_differ_only_by_letter_case_are_not_duplicated(self):
        records = {}
        add_record(records, "EDMR", "B", [("Toyota", "Yaris")], 1)
        add_record(records, "EDMR", "B", [("Toyota", "YARIS")], 1)

        self.assertEqual(records["EDMR"]["models"], [("Toyota", "Yaris")])

    def test_branded_model_replaces_same_unbranded_model(self):
        records = {}
        add_record(records, "EDMR", "B", [("", "Yaris")], 1)
        add_record(records, "EDMR", "B", [("Toyota", "Yaris")], 1)

        self.assertEqual(records["EDMR"]["models"], [("Toyota", "Yaris")])


class DepositRuleTests(TestCase):
    def test_every_confirmed_supplier_group_has_a_deposit_rule(self):
        self.assertEqual(len(DEPOSIT_AMOUNTS_PLN["01"]), 28)
        self.assertEqual(len(DEPOSIT_AMOUNTS_PLN["02"]), 20)
        self.assertEqual(len(DEPOSIT_AMOUNTS_PLN["03"]), 12)

    def test_confirmed_deposit_examples(self):
        self.assertEqual(default_deposit_amount("01", "PFAR"), Decimal("1000.00"))
        self.assertEqual(default_deposit_amount("02", "RLAR"), Decimal("2000.00"))
        self.assertEqual(
            default_deposit_amount("03", "BUS-9-SEATER-AUTOMATIC"),
            Decimal("1500.00"),
        )
