import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from customers.models import Customer
from suppliers.models import Supplier
from .models import Booking, OrderFileSync
from .order_file import (FIELDS, merge_fields, workbook_bytes, read_file, prepare_sync,
                         apply_sync, export_sync, create_snapshot)


def values(**kwargs):
    return {**dict.fromkeys(FIELDS,''),'firm':'T','name':'TEST CLIENT','gross':'123.00',
        'number':'TEST-001','status':'Обычный','pickup':'10/11/2026, 12:00, TEST AIRPORT',
        'return':'12/11/2026, 12:00, TEST AIRPORT',**kwargs}


def file_bytes(field):
    with field.open('rb') as handle:
        return handle.read()


def excel(row):
    return workbook_bytes([{'values':row,'key':'TEST-ROW','currency':'PLN'}])


class MergeTests(SimpleTestCase):
    def test_three_way_preserves_independent_changes_and_reports_collision(self):
        base=values()
        left={**base,'email':'excel@example.test'}
        right={**base,'phone':'123'}
        merged,conflicts=merge_fields(base,left,right)
        self.assertEqual(conflicts,[])
        self.assertEqual(merged['email'],'excel@example.test')
        self.assertEqual(merged['phone'],'123')
        _,conflicts=merge_fields(base,{**base,'gross':'246.00'},{**base,'gross':'369.00'})
        self.assertEqual(conflicts,['gross'])

    def test_first_merge_never_overwrites_different_nonempty_values(self):
        merged,conflicts=merge_fields(None,values(email='x@example.test'),values(email='y@example.test'))
        self.assertEqual(conflicts,['email'])


class OrderFileTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.setting=override_settings(MEDIA_ROOT=self.temp.name)
        self.setting.enable()
        self.addCleanup(self.setting.disable)
        self.backup=patch('bookings.order_file.database_backup',return_value=self.temp.name+'/test-backup.sqlite3')
        self.backup.start()
        self.addCleanup(self.backup.stop)
        self.user=get_user_model().objects.create_user('sync-owner',is_staff=True)
        self.supplier=Supplier.objects.create(supplier_name='TEST SUPPLIER',supplier_code='TEST',working_file_code='T')

    def test_preview_then_apply_historical_once_and_no_mail(self):
        run=prepare_sync(self.user,excel(values()))
        self.assertEqual(Booking.objects.count(),0)
        self.assertEqual(run.plan['rows'][0]['action'],'create')
        applied=apply_sync(run,self.user)
        self.assertEqual(Booking.objects.count(),1)
        booking=Booking.objects.get()
        self.assertEqual(booking.total_price_gross,Decimal('123'))
        self.assertEqual(booking.customer_name_snapshot,'TEST CLIENT')
        self.assertTrue(applied.result)
        with self.assertRaises(ValidationError):
            apply_sync(applied,self.user)
        again=prepare_sync(self.user,file_bytes(applied.result))
        self.assertEqual(again.plan['rows'][0]['action'],'same')
        from django.core import mail
        self.assertEqual(len(mail.outbox),0)

    def test_stale_preview_and_dual_price_edits_block_changes(self):
        run=apply_sync(prepare_sync(self.user,excel(values())),self.user)
        content=file_bytes(run.result)
        book=load_workbook(BytesIO(content))
        book['Заказы']['F2']=246
        output=BytesIO();book.save(output)
        preview=prepare_sync(self.user,output.getvalue())
        self.assertEqual(preview.plan['rows'][0]['action'],'update')
        Booking.objects.update(total_price_gross=369)
        with self.assertRaises(ValidationError):
            apply_sync(preview,self.user)
        preview=prepare_sync(self.user,output.getvalue())
        self.assertEqual(preview.plan['rows'][0]['action'],'conflict')
        self.assertEqual(Booking.objects.get().total_price_gross,Decimal('369'))

    def test_price_update_is_audited_and_preserves_price_components(self):
        run=apply_sync(prepare_sync(self.user,excel(values())),self.user)
        book=load_workbook(BytesIO(file_bytes(run.result)))
        book['Заказы']['F2']=150
        output=BytesIO();book.save(output)
        updated=apply_sync(prepare_sync(self.user,output.getvalue()),self.user)
        booking=Booking.objects.get()
        self.assertEqual(booking.vehicle_price_gross,Decimal('123'))
        self.assertEqual(booking.manual_adjustment_amount,Decimal('27'))
        self.assertEqual(booking.total_price_gross,Decimal('150'))
        self.assertEqual(booking.history_events.filter(description__contains='Excel').count(),2)

    def test_export_retains_unmatched_rows_and_never_imports_them(self):
        row=values(number='')
        first=export_sync(self.user,excel(row))
        self.assertEqual(Booking.objects.count(),0)
        second=export_sync(self.user)
        retained,_=read_file(file_bytes(second.result))
        self.assertEqual(len(retained),1)
        self.assertEqual(retained[0]['values']['name'],'TEST CLIENT')
        self.assertEqual(Booking.objects.count(),0)
        target=Path(self.temp.name)/'nightly.xlsx'
        create_snapshot(target)
        self.assertTrue(target.exists())

    def test_duplicate_rows_and_formula_text(self):
        content=workbook_bytes([{'values':values(),'key':'A'}, {'values':values(),'key':'B'}])
        run=prepare_sync(self.user,content)
        self.assertTrue(all(r['action']=='conflict' for r in run.plan['rows']))
        row=values(name='=TEST-NAME')
        parsed,_=read_file(excel(row))
        self.assertEqual(parsed[0]['values']['name'],'=TEST-NAME')

    def test_access_and_csrf_get_does_not_write(self):
        url=reverse('quotes:order_file')
        self.assertEqual(self.client.get(url).status_code,302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(OrderFileSync.objects.count(),0)
        ordinary=get_user_model().objects.create_user('ordinary')
        self.client.force_login(ordinary)
        self.assertEqual(self.client.get(url).status_code,403)
