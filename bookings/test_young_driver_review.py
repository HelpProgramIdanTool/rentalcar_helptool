from decimal import Decimal

from django.test import TestCase
from django.core import mail
from django.urls import reverse

from suppliers.models import SupplierExtra, SupplierExtraRate
from . import test_manual as manual_data
from .models import Booking


class YoungDriverReviewTests(TestCase):
    setUp = manual_data.ManualBookingTests.setUp
    review = manual_data.ManualBookingTests.review
    confirm = manual_data.ManualBookingTests.confirm

    def tariff(self, *, amount=10, calculation_type='PER_DRIVER_DAY', maximum=None):
        extra = SupplierExtra.objects.create(supplier=self.supplier,extra_code='YOUNG_DRIVER',name='TEST Young driver fee')
        SupplierExtraRate.objects.create(extra=extra,calculation_type=calculation_type,amount_gross=amount,
            maximum_amount_gross=maximum,valid_from='2026-01-01')
        return extra

    def two_young(self, **changes):
        return dict(driver_count=2,driver_1_name='TEST FIRST DRIVER',driver_2_name='TEST SECOND DRIVER',
            driver_1_young='on',driver_2_young='on',return_date='2026-10-05',**changes)

    def test_two_young_without_tariff_cannot_silently_get_manual_price(self):
        response = self.client.post(self.url,{**self.data,**self.two_young(),
            'manual_adjustment_amount':'100','manual_adjustment_label':'TEST manual fee'})
        self.assertIsNone(response.context['review_token'])
        self.assertContains(response,'Нет подтверждённого тарифа для молодых/новых водителей')
        self.assertFalse(Booking.objects.exists())

    def test_two_young_four_days_review_save_and_letter(self):
        extra = self.tariff()
        data,response = self.review(**self.two_young())
        self.assertEqual(response.context['result']['total'],Decimal('480'))
        self.confirm(data,response)
        booking = Booking.objects.get()
        fee = booking.extras.get(extra=extra)
        self.assertEqual(fee.quantity,2)
        self.assertEqual(fee.calculated_price_gross,80)
        self.assertEqual(booking.drivers.filter(young_driver_status=True).count(),2)
        body = self.client.get(reverse('quotes:supplier_message',args=[booking.pk])).context['body']
        self.assertIn('Young/new drivers (2): TEST FIRST DRIVER // TEST SECOND DRIVER',body)
        self.assertIn('TEST Young driver fee x 2.00',body)

    def test_daily_and_per_rental_rates_multiply_by_people_with_individual_cap(self):
        self.tariff(maximum=30)
        _,response = self.review(**self.two_young())
        self.assertEqual(response.context['result']['extras_total'],60)
        SupplierExtraRate.objects.filter(extra__supplier=self.supplier).update(calculation_type='PER_RENTAL',amount_gross=100,maximum_amount_gross=None)
        _,response = self.review(**self.two_young())
        self.assertEqual(response.context['result']['extras_total'],200)

    def test_manual_adjustment_description_is_visible_in_supplier_letter(self):
        data,response = self.review(manual_adjustment_label='TEST labelled surcharge',manual_adjustment_amount='100')
        self.confirm(data,response)
        body = self.client.get(reverse('quotes:supplier_message',args=[Booking.objects.get().pk])).context['body']
        self.assertIn('TEST labelled surcharge',body)
        self.assertIn('100',body)

    def test_balanced_price_for_one_driver_is_blocked_when_two_are_marked(self):
        from .message_content import booking_price_error
        extra = self.tariff()
        data,response = self.review(**self.two_young())
        self.confirm(data,response)
        booking = Booking.objects.get()
        booking.extras.filter(extra=extra).update(quantity=1,calculated_price_gross=40)
        snapshot = {**booking.source_quote_snapshot,'total':'440'}
        Booking.objects.filter(pk=booking.pk).update(total_price_gross=440,source_quote_snapshot=snapshot)
        booking.refresh_from_db()
        self.assertTrue(booking_price_error(booking))
        url = reverse('quotes:supplier_message',args=[booking.pk])
        page = self.client.get(url)
        for action in ['send','mark_manual']:
            sent = self.client.post(url,dict(action=action,recipient='test@example.invalid',subject='TEST',
                body=page.context['body'],send_token=page.context['send_token']))
            self.assertContains(sent,'Доплата за молодых/новых водителей не соответствует')
        self.assertFalse(mail.outbox)
        self.assertFalse(booking.supplier_deliveries.exists())

    def test_zero_price_still_names_young_drivers_and_update_letter_has_same_details(self):
        from .amendments import order_body
        self.tariff(amount=0)
        data,response = self.review(**self.two_young())
        self.confirm(data,response)
        booking = Booking.objects.get()
        self.assertEqual(booking.total_price_gross,400)
        self.assertIn('Young/new drivers (2): TEST FIRST DRIVER // TEST SECOND DRIVER',order_body(booking))

    def test_old_saved_message_without_young_driver_description_cannot_be_sent(self):
        self.tariff()
        data,response = self.review(**self.two_young())
        self.confirm(data,response)
        booking = Booking.objects.get()
        url = reverse('quotes:supplier_message',args=[booking.pk])
        page = self.client.get(url)
        old_body = '\n'.join(line for line in page.context['body'].splitlines() if not line.startswith('Young/new drivers'))
        response = self.client.post(url,dict(action='send',recipient='test@example.invalid',subject='TEST',
            body=old_body,send_token=page.context['send_token']))
        self.assertContains(response,'В письме отсутствует описание молодых/новых водителей')
        self.assertFalse(mail.outbox)

    def test_old_offer_for_one_young_driver_cannot_be_reused_for_two(self):
        from quotes.models import Quote, QuoteOption
        from quotes.price_validation import quote_price_issues
        extra = self.tariff()
        data,response = self.review(**self.two_young())
        self.confirm(data,response)
        booking = Booking.objects.get()
        quote = Quote.objects.create(customer=self.customer,pickup_datetime=booking.pickup_datetime,
            return_datetime=booking.return_datetime,pickup_city='Kraków',return_city='Kraków',
            pickup_service='CITY_BRANCH',return_service='CITY_BRANCH',extra_requests={'YOUNG_DRIVER':2})
        option = QuoteOption.objects.create(quote=quote,supplier=self.supplier,vehicle_group=self.group,
            comparison_class=self.group.comparison_classes.first(),total_price_gross=440,
            calculation_snapshot={'base':'400','extras_total':'40','lines':[
                {'extra_id':extra.pk,'quantity':'1','name':extra.name,'price':'40'}]})
        self.assertTrue(quote_price_issues(quote))
        option.total_price_gross = 480
        option.calculation_snapshot = {'base':'400','extras_total':'80','lines':[
            {'extra_id':extra.pk,'quantity':'2','name':extra.name,'price':'80'}]}
        option.save()
        self.assertEqual(quote_price_issues(quote),[])

    def test_configured_customer_service_name_translates_back_to_supplier_english_name(self):
        from quotes.models import Quote, QuoteOption
        from quotes.views import _quote_preview_context
        extra = self.tariff()
        extra.customer_name_he = 'TEST-NAME-HE'
        extra.name = 'TEST-NAME-EN'
        extra.save()
        data,response = self.review(**self.two_young())
        self.confirm(data,response)
        booking = Booking.objects.get()
        quote = Quote.objects.create(customer=self.customer,language='English',pickup_datetime=booking.pickup_datetime,
            return_datetime=booking.return_datetime,pickup_city='Kraków',return_city='Kraków')
        QuoteOption.objects.create(quote=quote,supplier=self.supplier,vehicle_group=self.group,
            comparison_class=self.group.comparison_classes.first(),total_price_gross=480,
            calculation_snapshot={'included_items':['TEST-NAME-HE × 2']})
        option = _quote_preview_context(quote)['options'][0]
        self.assertIn('TEST-NAME-EN × 2',option.display_included_items)
