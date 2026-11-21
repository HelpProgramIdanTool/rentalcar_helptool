from datetime import timedelta
from types import SimpleNamespace
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from suppliers.models import SupplierLocalBranch, RentalCountry, OfferCity, Supplier
from suppliers.test_recurring_prices import RecurringQuoteTests
from .forms import FirstInquiryForm
from .country_rules import route_context
from .services import calculate_quote_options


class LocalModeTests(TestCase):
    def setUp(self):
        RecurringQuoteTests.setUp(self)
        self.country=RentalCountry.objects.get(code='CZ')
        self.city=OfferCity.objects.create(name='TEST Czech city',label='TEST CITY',country='Czechia')
        self.mode=SupplierLocalBranch.objects.create(supplier=self.supplier,city=self.city,country=self.country,
            offer_mode_enabled=True,offer_mode_label='TEST LOCAL MODE',offer_mode_help='TEST MODE HELP',
            offer_mode_pricing_confirmed=True)
        self.data={'local_rental_branch':self.mode.pk,'suppliers':[self.supplier.pk],
            'vehicle_groups':[self.group.pk], 'pickup_date':'30-05-2027','pickup_time':'12:00',
            'return_date':'03-06-2027','return_time':'12:00','pickup_city':self.city.name,'return_city':self.city.name,
            'pickup_service':'AIRPORT','return_service':'AIRPORT','driver_count':1,
            'email':'test@example.com','full_name':'TEST CLIENT','preferred_language':'English'}

    def test_mode_sets_country_without_marking_local_trip_as_foreign(self):
        form=FirstInquiryForm(data={**self.data,'rental_country':'PL'})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['rental_country'],'CZ')
        self.assertFalse(form.cleaned_data['cross_border_requested'])
        self.assertIn('TEST LOCAL MODE',str(form['local_rental_branch']))

    def test_foreign_drive_remains_explicit_for_czech_rental(self):
        form=FirstInquiryForm(data={**self.data,'cross_border_requested':'on'})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertTrue(form.cleaned_data['cross_border_requested'])

    def test_czech_country_wording_supports_customer_offer_languages(self):
        from .country_rules import localize_country_text
        self.quote.rental_country='CZ'
        for source in ['outside of Poland','מחוץ לגבולות פולין','poza Polskę','за пределами Польши']:
            self.assertNotEqual(localize_country_text(source,self.quote),source)

    def test_mixed_country_handover_is_rejected_both_directions(self):
        for side in ['pickup','return']:
            form=FirstInquiryForm(data={**self.data,side+'_city':'Warszawa'})
            self.assertFalse(form.is_valid())
            self.assertIn(side+'_city',form.errors)

    def test_no_automatic_use_of_unconfirmed_prices(self):
        self.mode.offer_mode_pricing_confirmed=False;self.mode.save()
        form=FirstInquiryForm(data=self.data)
        self.assertFalse(form.is_valid());self.assertIn('local_rental_branch',form.errors)

    def test_other_suppliers_cannot_be_submitted_in_local_mode(self):
        other=Supplier.objects.create(supplier_code='TEST-OTHER-LOCAL',supplier_name='TEST OTHER')
        form=FirstInquiryForm(data={**self.data,'suppliers':[other.pk]})
        self.assertFalse(form.is_valid());self.assertIn('suppliers',form.errors)

    def test_calculation_guard_blocks_bypassing_form(self):
        quote=SimpleNamespace(rental_country='CZ',pickup_city=self.city.name,return_city=self.city.name,
            cross_border_requested=False,local_rental_branch=self.mode)
        self.assertFalse(route_context(quote,self.supplier)['unsupported'])
        self.mode.offer_mode_pricing_confirmed=False
        self.assertTrue(route_context(quote,self.supplier)['unsupported'])

    def test_unconfirmed_local_mode_cannot_produce_an_available_price(self):
        self.mode.offer_mode_pricing_confirmed=False;self.mode.save()
        self.quote.local_rental_branch=self.mode
        self.quote.rental_country='CZ'
        self.quote.pickup_city=self.city.name;self.quote.return_city=self.city.name
        results=calculate_quote_options(self.quote)
        self.assertTrue(results)
        self.assertFalse(any(result['available'] for result in results))

    def test_quote_saves_and_edit_retains_mode(self):
        user=get_user_model().objects.create_user(username='local-mode-test')
        self.client.force_login(user)
        response=self.client.post(reverse('quotes:new_inquiry'),self.data)
        self.assertEqual(response.status_code,302)
        from .models import Quote
        quote=Quote.objects.filter(customer__email='test@example.com').latest('pk')
        self.assertEqual(quote.local_rental_branch_id,self.mode.pk)
        self.assertEqual(quote.rental_country,'CZ')
        from .views import _quote_form_initial
        self.assertEqual(_quote_form_initial(quote)['local_rental_branch'],self.mode.pk)

    def test_live_price_preview_passes_the_mode_to_the_shared_calculator(self):
        from unittest.mock import patch
        user=get_user_model().objects.create_user(username='local-mode-preview')
        self.client.force_login(user)
        with patch('quotes.price_preview.calculate_quote_options', return_value=[]) as calculate:
            response=self.client.post(reverse('quotes:preview_prices'),self.data)
        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(calculate.called)
        quote=calculate.call_args.args[0]
        self.assertEqual(quote.local_rental_branch_id,self.mode.pk)
        self.assertEqual(quote.rental_country,'CZ')

    def test_owner_price_confirmation_is_limited_to_czech_car_free(self):
        from django.apps import apps
        from importlib import import_module
        supplier,_=Supplier.objects.get_or_create(supplier_name='Car Free',defaults={'supplier_code':'TEST-CF-CONFIRM'})
        branch=SupplierLocalBranch.objects.create(supplier=supplier,city=self.city,country=self.country,
            offer_mode_label='TEST-CONFIG',offer_mode_pricing_confirmed=False)
        self.mode.offer_mode_pricing_confirmed=False;self.mode.save()
        confirm=import_module('suppliers.migrations.0063_confirm_czech_supplier_tariffs').confirm
        confirm(apps,None);confirm(apps,None)
        branch.refresh_from_db();self.mode.refresh_from_db()
        self.assertTrue(branch.offer_mode_pricing_confirmed)
        self.assertFalse(self.mode.offer_mode_pricing_confirmed)
        self.assertEqual(branch.offer_mode_label,'TEST-CONFIG')
