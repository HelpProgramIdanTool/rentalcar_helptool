from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management.base import CommandError
from django.test import TestCase

from customers.models import Customer
from employees.models import SubAgent
from quotes.models import Quote
from quotes.services import calculate_quote_options
from suppliers.models import Supplier, VehicleGroup, VehicleComparisonClass, PriceList, VehicleRate
from suppliers.management.commands.import_vehicle_rates import import_kaizen


class FakeSheet:
    def __init__(self, low, high):
        self.rows = [[None] * 9 for _ in range(92)]
        self.rows[1][0] = "HIGH SEASON - WITH COMFORT PACKAGE"
        self.rows[63][0] = "LOW SEASON - WITH COMFORT PACKAGE"
        for row, amount in ((4, high), (66, low)):
            self.rows[row][1] = "TEST-A; TEST-B"
            self.rows[row][4:9] = [amount] * 5

    def cell(self, row, column):
        return SimpleNamespace(value=self.rows[row - 1][column - 1])

    def iter_rows(self, **kwargs):
        return iter(self.rows)


class FakeWorkbook(dict):
    @property
    def sheetnames(self):
        return list(self)

    def close(self):
        pass


class KaizenSubagentImportTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_name="Kaizen Rent", supplier_code="TEST", subagent_pricing_method="DEDICATED",
        )
        self.groups = [VehicleGroup.objects.create(supplier=self.supplier, group_code=code)
                       for code in ("TEST-A", "TEST-B")]
        self.workbook = FakeWorkbook(Idan=FakeSheet(100, 200), Subagents=FakeSheet(120, 240))
        self.loader = patch(
            "suppliers.management.commands.import_vehicle_rates.load_workbook",
            return_value=self.workbook,
        )
        self.loader.start()
        self.addCleanup(self.loader.stop)

    def test_separate_prices_reimport_and_quote_selection(self):
        standard, _ = import_kaizen(Path("invented.xlsx"))
        partner, count = import_kaizen(Path("invented.xlsx"), audience=PriceList.Audience.SUBAGENT)
        self.assertEqual(count, 30)
        self.assertNotEqual(standard.pk, partner.pk)
        self.assertEqual(partner.audience, "SUBAGENT")
        self.assertEqual(partner.effective_to, date(2026, 12, 31))
        import_kaizen(Path("invented.xlsx"), audience=PriceList.Audience.SUBAGENT)
        self.assertEqual(VehicleRate.objects.count(), 60)
        comparison = VehicleComparisonClass.objects.create(code="TEST-COMPARE", name="Test class")
        comparison.vehicle_groups.add(*self.groups)
        quote = Quote.objects.create(
            customer=Customer.objects.create(email="test@example.com"),
            pickup_datetime=datetime(2026, 10, 11, 10, tzinfo=ZoneInfo("Europe/Warsaw")),
            return_datetime=datetime(2026, 10, 14, 10, tzinfo=ZoneInfo("Europe/Warsaw")),
        )
        quote.requested_vehicle_classes.add(comparison)
        quote.requested_vehicle_groups.add(*self.groups)
        self.assertEqual({o["daily_rate"] for o in calculate_quote_options(quote)}, {Decimal(100)})
        quote.sub_agent = SubAgent.objects.create(name="Test agent", code_prefix="TA")
        quote.save()
        self.assertEqual({o["daily_rate"] for o in calculate_quote_options(quote)}, {Decimal(120)})
        self.assertEqual({o["price_audience"] for o in calculate_quote_options(quote)}, {"SUBAGENT"})
        quote.pickup_datetime = quote.pickup_datetime.replace(month=7)
        quote.return_datetime = quote.return_datetime.replace(month=7)
        quote.save()
        self.assertEqual({o["daily_rate"] for o in calculate_quote_options(quote)}, {Decimal(240)})

    def test_invalid_subagent_rate_rolls_back_without_changing_standard_rates(self):
        standard, _ = import_kaizen(Path("invented.xlsx"))
        before = list(VehicleRate.objects.values_list("pk", "daily_rate_gross"))
        self.workbook["Subagents"].rows[66][6] = None
        with self.assertRaises(CommandError):
            import_kaizen(Path("invented.xlsx"), audience=PriceList.Audience.SUBAGENT)
        self.assertEqual(list(VehicleRate.objects.values_list("pk", "daily_rate_gross")), before)
        self.assertFalse(PriceList.objects.filter(audience="SUBAGENT").exists())

    def test_missing_subagent_sheet_does_not_fall_back_to_idan(self):
        del self.workbook["Subagents"]
        with self.assertRaises(CommandError):
            import_kaizen(Path("invented.xlsx"), audience=PriceList.Audience.SUBAGENT)
        self.assertFalse(PriceList.objects.filter(supplier=self.supplier).exists())
