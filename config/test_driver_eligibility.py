from django.test import SimpleTestCase
from .driver_eligibility import assess_drivers, validate_driver_details


class DriverEligibilityTests(SimpleTestCase):
    def assess(self, age, months, minimum_age=18, minimum_months=0, **rules):
        return assess_drivers({'exception': True, 'drivers': [{'age': age, 'license_months': months}]},
            minimum_age=minimum_age, minimum_license_months=minimum_months, rules={'version': 1, **rules})

    def test_minimum_limits_are_inclusive(self):
        self.assertTrue(self.assess(21, 12, 21, 12).eligible)
        self.assertFalse(self.assess(20, 12, 21, 12).eligible)
        self.assertFalse(self.assess(21, 11, 21, 12).eligible)

    def test_both_fee_conditions_count_person_once(self):
        result = self.assess(22, 4, surcharge_age_below=24, surcharge_license_months_below=12)
        self.assertEqual(result.charged_drivers, 1)

    def test_age_and_experience_boundaries(self):
        self.assertEqual(self.assess(23, 12, surcharge_age_below=24).charged_drivers, 1)
        self.assertEqual(self.assess(24, 11, surcharge_license_months_below=12).charged_drivers, 1)
        self.assertEqual(self.assess(21, 0, surcharge_age_below=21).charged_drivers, 0)
        self.assertFalse(self.assess(22, 5, minimum_months=6).eligible)
        self.assertTrue(self.assess(22, 6, minimum_months=6).eligible)

    def test_each_person_counts_separately(self):
        details = {'exception': True, 'drivers': [{'age': 19, 'license_months': 6}] * 2}
        result = assess_drivers(details, minimum_age=18, minimum_license_months=0,
            rules={'surcharge_age_below': 21})
        self.assertEqual(result.charged_drivers, 2)

    def test_missing_or_malformed_details_do_not_invent_ages(self):
        for value in ({'exception': True}, {'exception': False, 'drivers': [{}]},
                      {'exception': True, 'drivers': [{'age': True, 'license_months': 2}]}):
            with self.assertRaises(ValueError):
                validate_driver_details(value)
        self.assertEqual(validate_driver_details({}), {})

    def test_unconfigured_supplier_cannot_accept_new_declaration(self):
        result = assess_drivers({'exception': False}, minimum_age=None, minimum_license_months=None, rules={})
        self.assertFalse(result.eligible)

    def test_invalid_threshold_does_not_silently_allow_driver(self):
        result = self.assess(22, 4, surcharge_age_below='24')
        self.assertFalse(result.eligible)
