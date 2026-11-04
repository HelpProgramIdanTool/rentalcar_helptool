from unittest.mock import patch
from django.core import mail
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from . import test_manual as manual_tests
from .models import Booking, BookingAmendment
from suppliers.models import Supplier, VehicleGroup, PriceList, PriceSeason, PriceDayRange, VehicleRate


class AmendmentMessageTests(SimpleTestCase):
    def test_changed_line_is_highlighted_and_untrusted_text_is_escaped(self):
        from .amendments import message
        item=message('UPDATE','test@example.test','UPDATE ORDER TEST',
                     'Unchanged\nFlight <script>TEST</script>', 'Unchanged\nOld flight')
        self.assertIn('Unchanged<br>',item['html'])
        self.assertIn('<u>Flight &lt;script&gt;TEST&lt;/script&gt;</u>',item['html'])
        self.assertNotIn('<script>',item['html'])

    def test_new_order_does_not_highlight_every_line_as_changed(self):
        from .amendments import message
        item=message('NEW','test@example.test','NEW ORDER','TEST DRIVER\nTEST CAR')
        self.assertNotIn('<strong',item['html'])


class AmendmentTests(TestCase):
    def setUp(self):
        manual_tests.ManualBookingTests.setUp(self)
        response = self.client.post(self.url, self.data)
        self.client.post(self.url, {**self.data, 'action':'create', 'confirm_price':'yes',
                                  'review_token':response.context['review_token']})
        self.booking = Booking.objects.get()
        Booking.objects.filter(pk=self.booking.pk).update(status='CONFIRMED', supplier_booking_number='OLD-123')
        self.booking.refresh_from_db()
        self.url = reverse('quotes:edit_booking', args=[self.booking.pk])

    def prepare(self, **changes):
        data = {**self.data, **changes}
        response = self.client.post(self.url, data)
        self.assertIsNotNone(response.context['review_token'], response.context['form'].errors)
        response = self.client.post(self.url, {**data, 'action':'create', 'confirm_price':'yes',
            'review_token': response.context['review_token']})
        self.assertEqual(response.status_code, 302)
        return BookingAmendment.objects.latest('pk'), response.url

    def second_supplier(self):
        supplier = Supplier.objects.create(supplier_code='TEST-B',supplier_name='SECOND TEST',booking_email='new@example.test')
        group = VehicleGroup.objects.create(supplier=supplier,group_code='B',group_name='SECOND CAR',deposit_amount=200)
        group.comparison_classes.set(self.group.comparison_classes.all())
        price = PriceList.objects.create(supplier=supplier,name='TEST',version='TEST',effective_from='2026-01-01',status='ACTIVE')
        season = PriceSeason.objects.create(price_list=price,season_code='ALL',season_name='TEST',rental_date_from='2026-01-01')
        days = PriceDayRange.objects.create(price_list=price,range_code='ALL',label='TEST',days_from=1)
        VehicleRate.objects.create(season=season,day_range=days,vehicle_group=group,daily_rate_gross=200)
        return supplier,group

    def test_prefilled_page_and_detail_link(self):
        response=self.client.get(self.url)
        self.assertEqual(response.context['form']['customer_name'].value(),'Test Customer')
        self.assertEqual(response.context['form']['driver_1_name'].value(),'Test Driver')
        self.assertEqual(response.context['form']['vehicle_group'].value(),self.group.pk)
        detail=self.client.get(reverse('quotes:booking_detail',args=[self.booking.pk]))
        self.assertContains(detail,self.url)
        self.assertNotContains(detail, f'/admin/bookings/booking/{self.booking.pk}/change/')

    def test_update_keeps_identity_and_number_and_highlights_added_flight(self):
        amendment,url=self.prepare(flight_number='TEST-FLIGHT')
        self.booking.refresh_from_db()
        self.assertEqual(Booking.objects.count(),1)
        self.assertEqual(self.booking.supplier_booking_number,'OLD-123')
        self.assertEqual(self.booking.flight_number,'TEST-FLIGHT')
        self.assertEqual(amendment.messages[0]['subject'],'UPDATE ORDER OLD-123')
        self.assertIn('TEST-FLIGHT',amendment.messages[0]['html'])
        self.assertIn('<strong',amendment.messages[0]['html'])
        self.assertEqual(amendment.before['fields']['flight_number'],'')
        self.assertEqual(len(mail.outbox),0)
        response=self.client.get(url)
        self.assertContains(response,'UPDATE ORDER OLD-123')
        self.client.post(url,{'message_index':'0','recipient':'test@example.test'})
        self.client.post(url,{'message_index':'0','recipient':'test@example.test'})
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].alternatives[0].mimetype,'text/html')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status,'UPDATE_PENDING')

    def test_supplier_switch_prepares_independent_cancellation_and_new_order(self):
        supplier,group=self.second_supplier()
        amendment,url=self.prepare(supplier=supplier.pk,vehicle_group=group.pk)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.supplier,supplier)
        self.assertEqual(self.booking.supplier_booking_number,'')
        self.assertEqual(self.booking.total_price_gross,600)
        self.assertEqual([m['kind'] for m in amendment.messages],['CANCEL','NEW'])
        self.assertEqual(amendment.messages[0]['subject'],'CANCEL ORDER OLD-123')
        self.assertIn('Test car',amendment.messages[0]['body'])
        self.assertIn('SECOND CAR',amendment.messages[1]['body'])
        self.assertNotIn('OLD-123',amendment.messages[1]['body'])
        self.client.post(url,{'message_index':'1','recipient':'new@example.test'})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status,'WAITING_CONFIRMATION')
        with patch('bookings.amendments.EmailMultiAlternatives.send',side_effect=OSError('TEST')):
            self.client.post(url,{'message_index':'0','recipient':'old@example.test'})
        amendment.refresh_from_db()
        self.assertEqual([m['status'] for m in amendment.messages],['FAILED','SENT'])
        self.assertEqual(len(mail.outbox),1)

    def test_stale_review_cannot_overwrite_intervening_changes(self):
        review=self.client.post(self.url,self.data)
        Booking.objects.filter(pk=self.booking.pk).update(flight_number='OTHER-CHANGE')
        response=self.client.post(self.url,{**self.data,'action':'create','confirm_price':'yes',
            'review_token':review.context['review_token']})
        self.assertEqual(response.status_code,200)
        self.assertFalse(BookingAmendment.objects.exists())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.flight_number,'OTHER-CHANGE')

    def test_other_operator_cannot_edit_or_send(self):
        from django.contrib.auth import get_user_model
        amendment,url=self.prepare(flight_number='TEST')
        self.client.force_login(get_user_model().objects.create_user(username='other'))
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.post(url,{'message_index':'0','recipient':'bad@example.test'}).status_code,404)

    def test_revising_unsent_switch_keeps_original_cancellation(self):
        supplier,group=self.second_supplier()
        amendment,url=self.prepare(supplier=supplier.pk,vehicle_group=group.pk)
        response=self.client.get(self.url)
        self.assertEqual(response.status_code,200)
        revised,unused=self.prepare(supplier=supplier.pk,vehicle_group=group.pk,flight_number='REVISED')
        self.assertEqual(revised.pk,amendment.pk)
        self.assertEqual(BookingAmendment.objects.count(),1)
        self.assertEqual(revised.messages[0]['subject'],'CANCEL ORDER OLD-123')
        self.assertNotIn('REVISED',revised.messages[0]['body'])
        self.assertIn('REVISED',revised.messages[1]['body'])
        self.assertEqual(len(mail.outbox),0)

    def test_failed_mail_requires_confirmation_before_retry(self):
        amendment,url=self.prepare(flight_number='TEST')
        with patch('bookings.amendments.EmailMultiAlternatives.send',side_effect=OSError('TEST')):
            self.client.post(url,{'message_index':'0','recipient':'test@example.test'})
        self.client.post(url,{'message_index':'0','recipient':'test@example.test'})
        self.assertEqual(len(mail.outbox),0)
        self.client.post(url,{'message_index':'0','recipient':'test@example.test','confirm_retry':'yes'})
        self.assertEqual(len(mail.outbox),1)
        amendment.refresh_from_db()
        self.assertEqual(amendment.messages[0]['status'],'SENT')

    def test_version_is_visible_and_history_requires_login(self):
        from config.version import APP_VERSION
        self.assertContains(self.client.get(self.url),APP_VERSION)
        self.assertContains(self.client.get(reverse('quotes:version_history')),APP_VERSION)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('quotes:version_history')).status_code,302)
