from django.contrib import admin
from django.test import TestCase

from .models import Supplier


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
