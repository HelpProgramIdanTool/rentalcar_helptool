from types import SimpleNamespace

from django.test import SimpleTestCase

from .quote_conversion import extra_calculation_errors


class ExtraCalculationErrorTests(SimpleTestCase):
    def result(self, **values):
        return {"supplier": SimpleNamespace(supplier_name="TEST-SUPPLIER"),
                "unavailable_requests": [], "extra_lines": [], **values}

    def test_missing_navigation_names_the_service_and_supplier(self):
        errors = extra_calculation_errors(self.result(unavailable_requests=["NAVIGATION"]))
        self.assertEqual(len(errors), 1)
        self.assertIn("GPS / навигация", errors[0])
        self.assertIn("TEST-SUPPLIER", errors[0])
        self.assertIn("снимите её выбор", errors[0])

    def test_all_problems_are_shown_without_repeating_the_same_error(self):
        errors = extra_calculation_errors(self.result(unavailable_requests=["NAVIGATION", "NAVIGATION"],
            extra_lines=[{"name": "TEST-EXTRA", "warning": "TEST-REASON"}]))
        self.assertEqual(len(errors), 2)
        self.assertIn("TEST-EXTRA: TEST-REASON", errors[1])

    def test_successful_services_have_no_error(self):
        self.assertEqual(extra_calculation_errors(self.result(extra_lines=[{"name": "TEST-OK", "price": 100}])), [])

    def test_unknown_service_code_is_retained_for_diagnosis(self):
        self.assertIn("TEST-UNKNOWN", extra_calculation_errors(self.result(unavailable_requests=["TEST-UNKNOWN"]))[0])
