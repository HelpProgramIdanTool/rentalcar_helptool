from datetime import date, datetime, timezone as dt_timezone
from types import SimpleNamespace as NS
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from suppliers.models import AnalyticsCity, Supplier, SupplierLocation
from .geography import Places, analyze, cross_border, month_grid
from .models import Booking


def fake_booking(**overrides):
    return NS(source_quote_snapshot={},pickup_location=None,return_location=None,
        pickup_location_text='',return_location_text='',pickup_address='',return_address='',
        hotel_name='',return_hotel_name='',extras=NS(all=lambda:[]),**overrides)


class GeographyCalculations(SimpleTestCase):
    def setUp(self):
        self.home=NS(pk=1,name='TEST-HOME',label='TEST-LABEL',country='Poland',aliases=['TEST-ALIAS'])
        self.foreign=NS(pk=2,name='TEST-FOREIGN-CITY',label='TEST-ABROAD',country='TEST-COUNTRY',aliases=[])
        self.places=Places([self.home,self.foreign])

    def test_aliases_are_read_from_data_and_foreign_is_not_tied_to_cross_border(self):
        booking=fake_booking()
        booking.pickup_location_text='TEST-ALIAS airport'
        result=self.places.resolve(booking,'pickup')
        self.assertEqual(result['city'],'TEST-LABEL')
        self.assertFalse(result['foreign'])
        booking.source_quote_snapshot={'request':{'return_city':'TEST-FOREIGN-CITY','cross_border_requested':False}}
        self.assertTrue(self.places.resolve(booking,'return')['foreign'])
        self.assertFalse(cross_border(booking))

    def test_ambiguous_and_unknown_text_does_not_invent_country(self):
        booking=fake_booking()
        booking.pickup_location_text='TEST-HOME to TEST-FOREIGN-CITY'
        self.assertIsNone(self.places.resolve(booking,'pickup')['foreign'])
        booking.pickup_location_text='AN UNKNOWN ADDRESS'
        self.assertEqual(self.places.resolve(booking,'pickup')['city'],'Не указано')

    def test_structured_place_and_hotel_near_airport(self):
        booking=fake_booking()
        booking.pickup_location=NS(city='TEST-HOME',country='Poland',location_type='AIRPORT',airport_code='TST',location_name='TEST DESK')
        result=self.places.resolve(booking,'pickup')
        self.assertIn('TST',result['place'])
        booking.pickup_location=None
        booking.pickup_location_text='TEST-ALIAS Hotel at airport'
        self.assertIn('Гостиница',self.places.resolve(booking,'pickup')['place'])

    def test_foreign_request_does_not_inherit_domestic_airport_used_for_pricing(self):
        booking=fake_booking()
        booking.source_quote_snapshot={'request':{'pickup_city':self.foreign.name,'pickup_service':'AIRPORT'}}
        booking.pickup_location=NS(city=self.home.name,country='Poland',location_type='AIRPORT',airport_code='TST',location_name='TEST DESK')
        result=self.places.resolve(booking,'pickup')
        self.assertTrue(result['foreign'])
        self.assertNotIn('TST',result['place'])
        booking.source_quote_snapshot={'request':{'pickup_city':'OTHER','pickup_service':'ADDRESS'}}
        booking.pickup_address=self.foreign.name+' TEST STREET'
        result=self.places.resolve(booking,'pickup')
        self.assertTrue(result['foreign'])
        self.assertIn('TEST STREET',result['place'])

    def test_cross_border_flag_extra_and_historical_text(self):
        booking=fake_booking()
        self.assertIsNone(cross_border(booking))
        booking.extras=NS(all=lambda:[NS(extra=NS(extra_code='CROSS_BORDER'))])
        self.assertTrue(cross_border(booking))
        booking.extras=NS(all=lambda:[])
        booking.source_quote_snapshot={'historical_import':{'raw':{'F':'Insurance + cross border to EU countries'}}}
        self.assertTrue(cross_border(booking))
        booking.source_quote_snapshot['historical_import']['raw']['F']='Insurance, no cross border'
        self.assertFalse(cross_border(booking))

    def test_unique_orders_and_calendar_counts_with_drafts(self):
        records=[dict(pickup={'city_key':'1','city':'TEST-LABEL','foreign':True,'place':'TEST-AIRPORT'},
            return_={'foreign':True},cross_border=False,draft=False,supplier='TEST-FIRM',
            time=timezone.make_aware(datetime(2026,11,10,12))) for _ in range(2)]
        for r in records:r['return']=r.pop('return_')
        records[1]['draft']=True
        summary=analyze(records)
        self.assertEqual(summary['counts']['foreign_either'],2)
        self.assertEqual(summary['counts']['cross_border'],0)
        weeks=month_grid(records,date(2026,11,1),date(2026,11,5))
        cell=next(c for w in weeks for c in w if c['date']==date(2026,11,10))
        self.assertEqual((cell['count'],cell['drafts']),(1,1))
        self.assertEqual(len(cell['groups']),1)


@override_settings(TIME_ZONE='Europe/Warsaw')
class GeographyPageTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('geo-owner',is_staff=True)
        self.supplier=Supplier.objects.create(supplier_code='GEO-TEST',supplier_name='TEST-GEO-FIRM')
        self.customer=Customer.objects.create(first_name='TEST',last_name='GEO')
        self.city=AnalyticsCity.objects.create(name='TEST-GEO-CITY',label='TEST-GEO-LABEL',country='TEST-FOREIGN')
        self.url=reverse('quotes:geography')
        self.clock=patch('bookings.geography.timezone.localdate',return_value=date(2026,11,5))
        self.clock.start();self.addCleanup(self.clock.stop)

    def booking(self,status='CONFIRMED',**changes):
        booking=Booking.objects.create(customer=self.customer,supplier=self.supplier,status=status,
            source_quote_snapshot={'historical_import':{'test':True},'request':{
                'pickup_city':self.city.name,'return_city':self.city.name,
                'pickup_service':'AIRPORT','cross_border_requested':True}})
        Booking.objects.filter(pk=booking.pk).update(pickup_datetime=timezone.make_aware(datetime(2026,11,10,12)),**changes)
        return booking

    def test_access(self):
        self.assertEqual(self.client.get(self.url).status_code,302)
        user=get_user_model().objects.create_user('geo-sales')
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_calendar_drilldown_filters_and_status_exclusions(self):
        booking=self.booking()
        for status in ['CANCELLED','NO_SHOW','DRAFT','COMPLETED']:
            self.booking(status)
        self.booking(is_archived=True)
        self.client.force_login(self.user)
        response=self.client.get(self.url,{'year':2026,'month':'2026-11','day':'2026-11-10'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['summary']['total'],2)  # confirmed + completed
        self.assertEqual(len(response.context['day_records']),1)
        self.assertEqual(response.context['cards'][2]['count'],2)  # not doubled for two foreign sides
        self.assertContains(response,'TEST-GEO-LABEL')
        self.assertContains(response,reverse('quotes:booking_detail',args=[booking.pk]))
        with_drafts=self.client.get(self.url,{'year':2026,'month':'2026-11','day':'2026-11-10','drafts':'1'})
        self.assertEqual(len(with_drafts.context['day_records']),2)
        metric=self.client.get(self.url,{'year':2026,'metric':'foreign_either'})
        self.assertEqual(len(metric.context['details']),2)
        filtered=self.client.get(self.url,{'year':2026,'supplier':'999999'})
        self.assertEqual(filtered.context['summary']['total'],0)
        self.assertEqual(self.client.get(self.url,{'month':'broken'}).status_code,400)
        booking.refresh_from_db()
        self.assertEqual(booking.status,'CONFIRMED')

    def test_calendar_uses_local_day_and_source_dates_are_not_money_estimates(self):
        booking=self.booking()
        Booking.objects.filter(pk=booking.pk).update(pickup_datetime=datetime(2026,11,10,23,30,tzinfo=dt_timezone.utc))
        self.client.force_login(self.user)
        response=self.client.get(self.url,{'year':2026,'month':'2026-11','day':'2026-11-11'})
        self.assertEqual(len(response.context['day_records']),1)
        Booking.objects.filter(pk=booking.pk).update(pickup_datetime=None)
        response=self.client.get(self.url,{'year':2026,'month':'2026-11'})
        self.assertEqual(response.context['unknown_dates'],1)
        self.assertEqual(response.context['summary']['total'],0)

    def test_source_dates_locations_and_calendar_year_are_independent_of_analysis_year(self):
        booking=self.booking()
        snapshot=booking.source_quote_snapshot
        snapshot['historical_import']['raw']={'B':'15/1/27, TEST-GEO-CITY airport'}
        Booking.objects.filter(pk=booking.pk).update(pickup_datetime=None,source_quote_snapshot=snapshot)
        self.client.force_login(self.user)
        response=self.client.get(self.url,{'year':2026,'month':'2027-01','day':'2027-01-15'})
        self.assertEqual(response.context['summary']['total'],0)
        self.assertEqual(len(response.context['day_records']),1)
        row=response.context['day_records'][0]
        self.assertTrue(row['date_from_source'])
        self.assertFalse(row['time_known'])
        place=row['pickup']['place']
        response=self.client.get(self.url,{'year':2027,'month':'2027-01','day':'2027-01-15','location':place})
        self.assertEqual(len(response.context['day_records']),1)
        response=self.client.get(self.url,{'year':2027,'month':'2027-01','day':'2027-01-15','location':'OTHER-PLACE'})
        self.assertEqual(response.context['day_records'],[])
        booking.refresh_from_db()
        self.assertIsNone(booking.pickup_datetime)
