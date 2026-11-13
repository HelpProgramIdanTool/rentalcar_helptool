from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from pathlib import Path
import json
from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from bookings.statistics import booking_summary
from quotes.inquiry_import import suitable_group
from suppliers.models import Supplier, VehicleGroup, FormVehicleCategory
from suppliers.form_categories import apply_mapping, category_map


class BatchCalculationTests(SimpleTestCase):
    def test_offer_alignment_is_explicit_for_both_directions(self):
        from django.template.loader import render_to_string
        for ltr,direction,alignment in [(False,'rtl','right'),(True,'ltr','left')]:
            html=render_to_string('quotes/quote_preview.html',{
                'is_email':True,'is_ltr':ltr,'is_english':ltr,
                'quote':SimpleNamespace(quote_number='TEST-OFFER',customer='TEST-CUSTOMER'),
                'introduction_blocks':[SimpleNamespace(block_key='INTRO',title='TEST-TITLE',content='TEST-BODY')]})
            self.assertIn(f'align="{alignment}"',html)
            self.assertIn(f'text-align:{alignment};white-space:pre-line',html)
            self.assertNotIn('align="center"',html)
            self.assertIn('TEST-BODY',html)
            self.assertNotIn('manifest.webmanifest',html)

    def test_monthly_totals_weight_average_and_separate_currency(self):
        data = [dict(supplier=s,currency=c,gross=Decimal(n),month=1,return_date=date(2026,1,2))
                for s,c,n in [('A','PLN','100'),('A','PLN','100'),('B','PLN','400'),('B','EUR','90')]]
        result=booking_summary(data,date(2026,1,3))
        totals={r['currency']:r for r in result['month_totals']}
        self.assertEqual(totals['PLN']['gross'],600)
        self.assertEqual(totals['PLN']['count'],3)
        self.assertEqual(totals['PLN']['average'],200)
        self.assertEqual(totals['EUR']['gross'],90)

    def test_explicit_membership_overrides_name_guesses_but_keeps_capacity(self):
        group=SimpleNamespace(pk=1,seats=5,transmission='AUTOMATIC')
        req={'passengers':4,'automatic':True,'categories':['TEST-CATEGORY']}
        self.assertTrue(suitable_group(group,req,{'TEST-CATEGORY':{1}}))
        self.assertFalse(suitable_group(group,req,{'TEST-CATEGORY':{2}}))
        self.assertFalse(suitable_group(group,{**req,'categories':['UNKNOWN']},{'TEST-CATEGORY':{1}}))
        self.assertFalse(suitable_group(group,{**req,'passengers':7},{'TEST-CATEGORY':{1}}))

    def test_icons_have_required_sizes_and_manifest_does_not_claim_offline(self):
        from PIL import Image
        base=Path(__file__).resolve().parents[1]/'quotes/static/quotes/app'
        for size in (192,512):
            with Image.open(base/f'icon-{size}.png') as image:
                self.assertEqual(image.size,(size,size))
        manifest=json.loads((base/'manifest.webmanifest').read_text())
        self.assertEqual(manifest['start_url'],'/')
        self.assertEqual(manifest['display'],'standalone')


class BatchMappingTests(TestCase):
    def test_chains_migration_enables_only_kaizen_and_preserves_existing_prices(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        from suppliers.models import SupplierExtra, SupplierExtraRate
        supplier=Supplier.objects.create(supplier_code='TEST-K',supplier_name='Kaizen Rent')
        extra=SupplierExtra.objects.create(supplier=supplier,extra_code='SNOW_CHAINS',name='TEST-CHAINS',is_active=False)
        rate=SupplierExtraRate.objects.create(extra=extra,amount_gross=100,calculation_type='PER_DAY',valid_from='2026-01-01')
        other=SupplierExtra.objects.create(supplier=self.supplier,extra_code='SNOW_CHAINS',name='TEST-OTHER',is_active=False)
        function=import_module('suppliers.migrations.0050_enable_kaizen_chains').enable_chains
        function(apps,SimpleNamespace(connection=connection))
        extra.refresh_from_db(); other.refresh_from_db(); rate.refresh_from_db()
        self.assertTrue(extra.is_active)
        self.assertFalse(other.is_active)
        self.assertEqual(rate.amount_gross,100)

    def setUp(self):
        import tempfile
        from django.test import override_settings
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        override=override_settings(MEDIA_ROOT=temporary.name)
        override.enable()
        self.addCleanup(override.disable)
        self.supplier=Supplier.objects.create(supplier_code='BATCH-TEST',supplier_name='TEST-SUPPLIER')
        self.group=VehicleGroup.objects.create(supplier=self.supplier,group_code='TEST-GROUP',group_name='TEST-GROUP-NAME',show_in_offers=False)
        self.payload={'mappings':[{'supplier':self.supplier.supplier_name,'group_code':self.group.group_code,'category':'TEST-CATEGORY'}]}

    def test_import_is_exact_repeatable_and_invalid_file_changes_nothing(self):
        self.assertEqual(apply_mapping(self.payload),{'categories':1,'memberships':1})
        apply_mapping(self.payload)
        self.assertEqual(category_map(),{'TEST-CATEGORY':{self.group.pk}})
        self.group.refresh_from_db()
        self.assertTrue(self.group.show_in_offers)
        bad={'mappings':self.payload['mappings']+[dict(self.payload['mappings'][0],group_code='NOT-REAL')]}
        with self.assertRaises(VehicleGroup.DoesNotExist):
            apply_mapping(bad)
        self.assertEqual(category_map(),{'TEST-CATEGORY':{self.group.pk}})

    def test_empty_category_membership_does_not_guess(self):
        FormVehicleCategory.objects.create(name='TEST-EMPTY')
        self.assertEqual(category_map(),{'TEST-EMPTY':set()})

    def test_owner_import_and_preview_are_separate_and_staff_cannot_write(self):
        url=reverse('category_upload')
        self.assertEqual(self.client.get(url).status_code,302)
        staff=get_user_model().objects.create_user('TEST-STAFF',is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code,403)
        staff.is_superuser=True; staff.save()
        def upload(): return SimpleUploadedFile('test.json',json.dumps(self.payload).encode(),content_type='application/json')
        response=self.client.post(url,{'mapping':upload()})
        self.assertEqual(response.status_code,200)
        self.assertFalse(FormVehicleCategory.objects.exists())
        self.client.post(url,{'mapping':upload(),'apply':'yes'})
        self.assertEqual(category_map(),{'TEST-CATEGORY':{self.group.pk}})
