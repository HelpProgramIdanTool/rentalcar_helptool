from types import SimpleNamespace

from django.test import SimpleTestCase

from quotes.inquiry_import import suitable_group


class VehicleGroupMatchingTests(SimpleTestCase):
    def test_three_requested_types_are_matched_separately(self):
        requirements = {
            "passengers": 2, "automatic": True, "manual": False,
            "categories": ["רכב קטן", "רכב סטנדרטי סדאן", "רכב היברידי"],
        }
        cases = [
            ("B_AUTO", "", "", True),
            ("D_SEDAN_AUTO", "", "", True),
            ("SUP_01_CLAH", "", "היברידי", True),
            ("SUV_MEDIUM_AUTO", "SUV", "", False),
            ("PREMIUM_SEDAN_AUTO", "SEDAN", "", False),
        ]
        for code, body, fuel, expected in cases:
            with self.subTest(code=code):
                group = SimpleNamespace(
                    seats=None, transmission="AUTOMATIC", body_type=body,
                    group_name=code, category="", fuel_type_note=fuel,
                    comparison_classes=SimpleNamespace(all=lambda: [SimpleNamespace(code=code)]),
                )
                self.assertEqual(suitable_group(group, requirements), expected)

    def test_sedan_class_counts_when_body_field_is_empty(self):
        group = SimpleNamespace(
            seats=None, transmission="AUTOMATIC", body_type="",
            group_name="D AUTOMATIC", category="",
            comparison_classes=SimpleNamespace(all=lambda: [SimpleNamespace(code="D_SEDAN_AUTO")]),
        )
        requirements = {
            "passengers": 2, "automatic": True, "manual": False,
            "categories": ["רכב סדאן סטנדרטי"],
        }
        self.assertTrue(suitable_group(group, requirements))

    def test_unrelated_class_is_not_mistaken_for_sedan(self):
        group = SimpleNamespace(
            seats=None, transmission="AUTOMATIC", body_type="",
            group_name="SUV PREMIUM", category="",
            comparison_classes=SimpleNamespace(all=lambda: [SimpleNamespace(code="PREMIUM_SUV_AUTO")]),
        )
        requirements = {
            "passengers": 2, "automatic": True, "manual": False,
            "categories": ["רכב סדאן סטנדרטי"],
        }
        self.assertFalse(suitable_group(group, requirements))
