from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class SupplierServiceSummaryTests(SimpleTestCase):
    def test_all_selected_services_share_summary_line_and_keep_details(self):
        booking = SimpleNamespace(source_quote_snapshot={'request': {'cross_border_requested': True}},
            child_seat_details=[{'age': '3', 'height': '95', 'type_number': 'TEST-TYPE'}])
        extras = [SimpleNamespace(supplier_visible_name=name, quantity=quantity,
                                  calculation_complete=True)
                  for name, quantity in [('TEST-SEAT', 2), ('TEST-GPS', 1), ('TEST-BOOSTER', 1)]]
        text = render_to_string('bookings/supplier_message.txt', {'booking': booking, 'extras': extras})
        summary = next(line for line in text.splitlines() if line.startswith('Additional driver'))
        self.assertIn('border crossing to EU countries', summary)
        for extra in extras:
            self.assertIn(f'{extra.supplier_visible_name} x {extra.quantity}', summary)
        self.assertIn('Child seat 1: age 3, height 95 cm, type/number TEST-TYPE', text)
        self.assertIn('\nTEST-SEAT x 2\n', text)

    def test_no_optional_services_has_no_trailing_separator(self):
        text = render_to_string('bookings/supplier_message.txt', {'booking': {}, 'extras': []})
        summary = next(line for line in text.splitlines() if line.startswith('Additional driver'))
        self.assertTrue(summary.endswith('unlimited mileage'))
