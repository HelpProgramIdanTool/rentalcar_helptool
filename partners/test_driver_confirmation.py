from types import SimpleNamespace
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from .live_workspace import confirm_driver_declaration


class PartnerDriverConfirmationTests(SimpleTestCase):
    def setUp(self):
        self.supplier = SimpleNamespace(minimum_driver_age=21, minimum_license_months=0,
            customer_conditions={'driver_rules': {'version': 1, 'surcharge_age_below': 24}})
        self.trip = {'driver_requirements': {'exception': True,
            'drivers': [{'age': 22, 'license_months': 4}]}}

    def test_matching_facts_are_returned_for_booking_storage(self):
        result = confirm_driver_declaration(self.trip, {'driver_1_age':22, 'driver_1_license_months':5}, self.supplier, 1)
        self.assertEqual(result['driver_1_age'],22)
        self.assertEqual(result['driver_requirements']['drivers'][0]['license_months'],5)

    def test_ineligible_driver_is_blocked_even_when_surcharge_count_matches(self):
        with self.assertRaises(ValidationError):
            confirm_driver_declaration(self.trip, {'driver_1_age':20, 'driver_1_license_months':4}, self.supplier, 1)

    def test_changed_surcharge_needs_new_quote(self):
        with self.assertRaises(ValidationError):
            confirm_driver_declaration(self.trip, {'driver_1_age':30, 'driver_1_license_months':100}, self.supplier, 1)

    def test_missing_facts_do_not_pass_confirmation(self):
        with self.assertRaises(ValidationError):
            confirm_driver_declaration(self.trip, {}, self.supplier, 1)
