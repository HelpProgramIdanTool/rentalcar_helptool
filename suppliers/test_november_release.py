import importlib
from types import SimpleNamespace
from django.apps import apps
from django.test import TestCase
from .models import Supplier, VehicleGroup, FormVehicleCategory


class NovemberReleaseConfigurationTests(TestCase):
    def test_medium_premium_suv_membership_is_exact_and_other_groups_unchanged(self):
        supplier = Supplier.objects.create(supplier_code='TEST-MM', supplier_name='MM Cars')
        group = VehicleGroup.objects.create(supplier=supplier, group_code='TEST', group_name='PREMIUM SUV')
        other = VehicleGroup.objects.create(supplier=supplier, group_code='OTHER', group_name='TEST OTHER')
        wrong = FormVehicleCategory.objects.create(name='TEST 9 SEATS')
        wrong.vehicle_groups.add(group,other)
        migration = importlib.import_module('suppliers.migrations.0057_correct_premium_suv_category')
        migration.correct(apps, None)
        self.assertEqual(list(group.form_categories.values_list('name', flat=True)), ['רכב פרמיום SUV בינוני'])
        self.assertTrue(wrong.vehicle_groups.filter(pk=other.pk).exists())
        migration.correct(apps, None)
        self.assertEqual(group.form_categories.count(), 1)

    def test_suspension_keeps_historical_group_record_and_other_supplier_active(self):
        supplier = Supplier.objects.create(supplier_code='TEST-K', supplier_name='Kaizen Rent')
        other_supplier = Supplier.objects.create(supplier_code='TEST-OTHER', supplier_name='TEST OTHER')
        group = VehicleGroup.objects.create(supplier=supplier, group_code='PFAH', group_name='TEST HYBRID')
        other = VehicleGroup.objects.create(supplier=other_supplier, group_code='PFAH', group_name='TEST OTHER')
        migration = importlib.import_module('suppliers.migrations.0051_suspend_unconfirmed_hybrid_group')
        migration.suspend_group(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        group.refresh_from_db()
        other.refresh_from_db()
        self.assertFalse(group.is_active)
        self.assertFalse(group.show_in_offers)
        self.assertTrue(other.is_active)
