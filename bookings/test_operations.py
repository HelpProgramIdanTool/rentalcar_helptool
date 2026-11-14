from datetime import date, datetime, timezone as dt_timezone
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from suppliers.models import AnalyticsCity, Supplier, SupplierLocation
from .geography import Places, operation_time
from .models import Booking
from .operations import collect_events, summarize_events


@override_settings(TIME_ZONE='Europe/Warsaw')
class OperationsSmallTests(SimpleTestCase):
    def booking(self, **changes):
        values = dict(pk=1, supplier_id=1, supplier='TEST-FIRM', source_quote_snapshot={},
            pickup_datetime=timezone.make_aware(datetime(2026,11,1,10)),
            return_datetime=timezone.make_aware(datetime(2026,11,3,10)),
            pickup_location=None,return_location=None,pickup_location_text='TEST-A',
            return_location_text='TEST-B',pickup_address='',return_address='',hotel_name='',return_hotel_name='')
        values.update(changes)
        return SimpleNamespace(**values)

    def places(self):
        return Places([SimpleNamespace(pk=1,name='TEST-A',label='TEST-LABEL-A',country='Poland',aliases=[]),
                       SimpleNamespace(pk=2,name='TEST-B',label='TEST-LABEL-B',country='Poland',aliases=[])])

    def test_each_event_uses_its_own_date_and_city_inclusive_boundaries(self):
        booking = self.booking()
        events, _ = collect_events([booking],self.places(),date(2026,11,1),date(2026,11,3))
        self.assertEqual([(e['side'],e['city']) for e in events], [('pickup','TEST-LABEL-A'),('return','TEST-LABEL-B')])
        rows = summarize_events(events)
        self.assertEqual(sum(r['pickup'] for r in rows),1)
        self.assertEqual(sum(r['returns'] for r in rows),1)
        only_returns, _ = collect_events([booking],self.places(),date(2026,11,3),date(2026,11,3))
        self.assertEqual([e['side'] for e in only_returns],['return'])

    def test_local_midnight_and_operation_city_filters(self):
        booking = self.booking(return_datetime=datetime(2026,11,2,23,30,tzinfo=dt_timezone.utc))
        events, _ = collect_events([booking],self.places(),date(2026,11,3),date(2026,11,3),operation='return',city='2')
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['time'].hour,0)
        wrong_city, _ = collect_events([booking],self.places(),date(2026,11,3),date(2026,11,3),operation='return',city='1')
        self.assertEqual(wrong_city,[])

    def test_historical_return_comes_from_c_not_pickup_or_money(self):
        booking = self.booking(pickup_datetime=None,return_datetime=None,
            source_quote_snapshot={'historical_import':{'raw':{'B':'01/11/26, 09:00 TEST-A','C':'03/11/26 TEST-B'}}})
        events, unknown = collect_events([booking],self.places(),date(2026,11,3),date(2026,11,3))
        self.assertEqual([e['side'] for e in events],['return'])
        self.assertTrue(events[0]['from_source'])
        self.assertFalse(events[0]['time_known'])
        self.assertFalse(unknown)
        booking.source_quote_snapshot['historical_import']['raw']['C'] = 'No date'
        self.assertEqual(operation_time(booking,'return'),(None,False))
        events, unknown = collect_events([booking],self.places(),date(2026,11,1),date(2026,11,3))
        self.assertEqual(len(events),1)
        self.assertEqual([e['side'] for e in unknown],['return'])


class OperationsPageTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_superuser(username='operations-owner',email='test@example.invalid',password='test-only')
        self.client.force_login(self.owner)
        self.customer = Customer.objects.create(first_name='TEST-CUSTOMER')
        self.supplier = Supplier.objects.create(supplier_code='TEST-OPERATIONS',supplier_name='TEST-FIRM')
        self.city_a = AnalyticsCity.objects.create(name='TEST-OP-A',label='TEST-CITY-A',country='Poland')
        self.city_b = AnalyticsCity.objects.create(name='TEST-OP-B',label='TEST-CITY-B',country='Poland')
        self.location_a = SupplierLocation.objects.create(supplier=self.supplier,location_code='TEST-A',location_name='TEST A',city=self.city_a.name)
        self.location_b = SupplierLocation.objects.create(supplier=self.supplier,location_code='TEST-B',location_name='TEST B',city=self.city_b.name)
        self.booking = self.make_booking()
        self.url = reverse('quotes:operations')
        self.query = dict(start='2026-11-01',end='2026-11-03')

    def make_booking(self, **changes):
        values = dict(customer=self.customer,supplier=self.supplier,status='CONFIRMED',supplier_booking_number='TEST-RESERVATION',
            pickup_datetime=timezone.make_aware(datetime(2026,11,1,10)),return_datetime=timezone.make_aware(datetime(2026,11,3,10)),
            pickup_location=self.location_a,return_location=self.location_b)
        values.update(changes)
        return Booking.objects.create(**values)

    def test_totals_two_operations_one_booking_and_drilldown_exact(self):
        response = self.client.get(self.url,self.query)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['totals'],dict(pickup=1,returns=1,operations=2,bookings=1))
        rows = response.context['rows']
        row = next(row for row in rows if row['returns'])
        detail = self.client.get(row['return_url'])
        self.assertEqual(len(detail.context['events']),row['returns'])
        self.assertEqual(detail.context['events'][0]['side'],'return')
        self.assertEqual(detail.context['events'][0]['city_key'],str(self.city_b.pk))
        self.assertTrue(detail.context['show_details'])

    def test_cancelled_no_show_archived_excluded_and_drafts_opt_in(self):
        for status in ['CANCELLED','NO_SHOW','DRAFT']:
            self.make_booking(status=status)
        archived = self.make_booking()
        Booking.all_objects.filter(pk=archived.pk).update(is_archived=True)
        response = self.client.get(self.url,self.query)
        self.assertEqual(response.context['totals']['bookings'],1)
        response = self.client.get(self.url,{**self.query,'drafts':'on'})
        self.assertEqual(response.context['totals']['bookings'],2)

    def test_supplier_city_and_daily_links_use_same_filters(self):
        other = Supplier.objects.create(supplier_code='TEST-OTHER',supplier_name='TEST-OTHER')
        self.make_booking(supplier=other)
        response = self.client.get(self.url,{**self.query,'supplier':self.supplier.pk,'city':self.city_b.pk})
        self.assertEqual(response.context['totals']['operations'],1)
        day_row = response.context['daily'][0]
        detail = self.client.get(day_row['return_url'])
        self.assertEqual(detail.context['totals']['operations'],day_row['returns'])
        self.assertEqual(detail.context['form'].cleaned_data['start'],date(2026,11,3))
        self.assertEqual(detail.context['form'].cleaned_data['end'],date(2026,11,3))

    def test_unmapped_city_labels_share_one_unknown_group_and_exact_drilldown(self):
        for index in [1,2]:
            location = SupplierLocation.objects.create(supplier=self.supplier,location_code=f'UNMAPPED-{index}',
                location_name=f'TEST UNKNOWN {index}',city=f'UNMAPPED CITY {index}')
            self.make_booking(pickup_location=location)
        response = self.client.get(self.url,{**self.query,'operation':'pickup','city':'unknown'})
        self.assertEqual(len(response.context['rows']),1)
        row = response.context['rows'][0]
        self.assertEqual(row['pickup'],2)
        detail = self.client.get(row['pickup_url'])
        self.assertEqual(len(detail.context['events']),2)

    def test_invalid_period_is_visible_and_does_not_show_unfiltered_results(self):
        response = self.client.get(self.url,dict(start='2026-11-05',end='2026-11-01'))
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(response.context['events'])
        self.assertContains(response,'Дата начала позже даты окончания.')

    def test_return_filter_uses_local_date_and_historical_missing_time_is_explicit(self):
        Booking.objects.filter(pk=self.booking.pk).update(return_datetime=datetime(2026,11,2,23,30,tzinfo=dt_timezone.utc))
        response = self.client.get(self.url,dict(start='2026-11-03',end='2026-11-03',operation='return'))
        self.assertEqual(response.context['totals']['returns'],1)
        Booking.objects.filter(pk=self.booking.pk).update(return_datetime=None,
            source_quote_snapshot={'historical_import':{'raw':{'C':'03/11/26 TEST-OP-B'}}})
        response = self.client.get(self.url,dict(start='2026-11-03',end='2026-11-03',operation='return',details='1'))
        self.assertEqual(response.context['totals']['returns'],1)
        self.assertContains(response,'Время не указано')
        self.assertNotContains(response,'03.11.2026 00:00')

    def test_main_statistics_links_to_report_and_translates_new_labels(self):
        response = self.client.get(reverse('quotes:statistics'))
        self.assertContains(response,self.url)
        for language, heading in [('en','Pickups and returns by period'),('pl','Wydania i zwroty w okresie')]:
            self.client.post(reverse('operator_language'), {'language':language})
            response = self.client.get(self.url,self.query)
            self.assertContains(response,heading)

    def test_permissions_and_no_customer_or_email_changes(self):
        from django.core import mail
        before = list(Booking.objects.values('pk','status','pickup_datetime','return_datetime'))
        self.client.get(self.url,{**self.query,'details':'1'})
        self.assertEqual(before,list(Booking.objects.values('pk','status','pickup_datetime','return_datetime')))
        self.assertFalse(mail.outbox)
        user = get_user_model().objects.create_user(username='operations-regular')
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url,self.query).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url,self.query).status_code,302)
