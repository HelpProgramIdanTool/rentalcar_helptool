from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from suppliers.deposit_rules import default_deposit_amount
from suppliers.models import VehicleGroup


class DepositTests(SimpleTestCase):
    def test_each_group_uses_its_own_configured_amount(self):
        first = VehicleGroup(deposit_amount=Decimal("120"))
        second = VehicleGroup(deposit_amount=Decimal("340"))
        self.assertEqual(first.effective_deposit_amount, Decimal("120"))
        self.assertEqual(second.effective_deposit_amount, Decimal("340"))

    def test_zero_deposit_is_not_missing(self):
        group = VehicleGroup(deposit_amount=Decimal("0"))
        self.assertEqual(group.effective_deposit_amount, Decimal("0"))

    def test_unset_deposit_remains_unknown(self):
        self.assertIsNone(VehicleGroup().effective_deposit_amount)

    def test_linked_group_uses_deposit_of_its_tariff_group(self):
        tariff = VehicleGroup(deposit_amount=Decimal("120"))
        group = VehicleGroup(rate_source_group=tariff, deposit_amount=Decimal("340"))
        self.assertEqual(group.effective_deposit_amount, Decimal("120"))
        tariff.deposit_amount = Decimal("0")
        self.assertEqual(group.effective_deposit_amount, Decimal("0"))

    def test_fallback_reads_mapping_and_does_not_guess_unknown_groups(self):
        # Invent values instead of tying a test to a supplier's real deposit.
        with patch("suppliers.deposit_rules.DEPOSIT_AMOUNTS_PLN", {
            "TEST": {"SMALL": Decimal("120"), "LARGE": Decimal("340"), "FREE": Decimal("0")},
        }):
            self.assertEqual(default_deposit_amount("TEST", "SMALL"), Decimal("120"))
            self.assertEqual(default_deposit_amount("TEST", "LARGE"), Decimal("340"))
            self.assertEqual(default_deposit_amount("TEST", "FREE"), Decimal("0"))
            self.assertIsNone(default_deposit_amount("TEST", "UNKNOWN"))
            self.assertIsNone(default_deposit_amount("UNKNOWN", "SMALL"))
