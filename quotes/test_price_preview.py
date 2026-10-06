from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.template.loader import render_to_string
from suppliers import test_recurring_prices as starting_data
from suppliers.models import SupplierExtra, SupplierExtraRate
from customers.models import Customer
from .models import Quote, QuoteOption
from .services import calculate_quote_options
from .views import _quote_preview_context


class PricePreviewTests(TestCase):
    def setUp(self):
        starting_data.RecurringQuoteTests.setUp(self)
        self.client.force_login(get_user_model().objects.create_user(username='preview-test'))
        self.url=reverse('quotes:preview_prices')
        self.data={'suppliers':[self.supplier.pk], 'pickup_date':'30-05-2027','pickup_time':'12:00',
                   'return_date':'03-06-2027','return_time':'12:00','pickup_city':'Kraków','return_city':'Kraków',
                   'pickup_service':'AIRPORT','return_service':'AIRPORT','driver_count':2}

    def test_preview_matches_final_calculation_and_creates_no_records(self):
        before=(Quote.objects.count(),Customer.objects.count(),QuoteOption.objects.count())
        response=self.client.post(self.url,self.data)
        self.assertEqual(response.status_code,200,response.content)
        price=response.json()['prices'][str(self.group.pk)]
        final,=calculate_quote_options(self.quote)
        self.assertEqual(Decimal(price['total']),final['total'])
        self.assertEqual(price['currency'],final['currency'])
        self.assertEqual(before,(Quote.objects.count(),Customer.objects.count(),QuoteOption.objects.count()))

    def test_live_price_includes_night_service_and_requested_seat_quantity(self):
        for code,amount,kind in [('OUT_OF_HOURS',43,'PER_UNIT'),('CHILD_SEAT',5,'PER_DAY')]:
            extra=SupplierExtra.objects.create(supplier=self.supplier,extra_code=code,name='TEST-'+code)
            SupplierExtraRate.objects.create(extra=extra,amount_gross=amount,calculation_type=kind,valid_from=date(2026,1,1))
        response=self.client.post(self.url,{**self.data,'return_time':'07:00','extra_choices':['CHILD_SEAT'],'child_seat_quantity':2})
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(Decimal(response.json()['prices'][str(self.group.pk)]['total']),Decimal(400+28+43+40))

    def test_missing_requested_extra_does_not_show_partial_total(self):
        response=self.client.post(self.url,{**self.data,'extra_choices':['CHILD_SEAT'],'child_seat_quantity':1})
        price=response.json()['prices'][str(self.group.pk)]
        self.assertFalse(price['available'])
        self.assertNotIn('total',price)

    def test_invalid_dates_clear_prices(self):
        response=self.client.post(self.url,{**self.data,'return_date':'01-05-2027'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(response.json()['prices'],{})

    def test_unselected_supplier_is_not_priced_and_login_is_required(self):
        response=self.client.post(self.url,{**self.data,'suppliers':[]})
        self.assertEqual(response.json()['prices'],{})
        self.client.logout()
        self.assertEqual(self.client.post(self.url,self.data).status_code,302)

    def test_badge_comes_from_supplier_data_in_html_and_plain_text(self):
        self.supplier.offer_badges={'Hebrew':['TEST-AGE-BADGE']}
        self.supplier.save()
        self.quote.language='Hebrew'
        self.quote.save()
        option=QuoteOption.objects.create(quote=self.quote,supplier=self.supplier,vehicle_group=self.group,
            comparison_class=self.comparison,total_price_gross=428,supplier_name_snapshot='TEST-SUPPLIER')
        context=_quote_preview_context(self.quote,is_email=True)
        for template in ('quotes/quote_preview.html','quotes/quote_email.txt'):
            self.assertIn('TEST-AGE-BADGE',render_to_string(template,context))
        self.supplier.offer_badges={}
        self.supplier.save()
        context=_quote_preview_context(self.quote,is_email=True)
        self.assertNotIn('TEST-AGE-BADGE',render_to_string('quotes/quote_preview.html',context))

    def test_extras_appear_before_vehicle_and_supplier_choices(self):
        html=self.client.get(reverse('quotes:new_inquiry')).content.decode()
        self.assertLess(html.index('name="extra_choices"'),html.index('name="suppliers"'))
        self.assertLess(html.index('name="cross_border_requested"'),html.index('name="vehicle_groups"'))
        self.assertIn('quotes/price_preview.js',html)
