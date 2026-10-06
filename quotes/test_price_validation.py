from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from suppliers import test_recurring_prices as starting_data
from suppliers.models import SupplierExtra, SupplierExtraRate
from .models import QuoteOption
from .price_validation import saved_fee_amount, quote_price_issues


class SavedFeeTests(SimpleTestCase):
    def test_identifier_survives_renaming_and_legacy_names_still_match(self):
        extra = SimpleNamespace(pk=7, name='NEW-NAME')
        self.assertEqual(saved_fee_amount([{'extra_id':7,'name':'OLD-NAME','price':'43'}],extra),43)
        self.assertEqual(saved_fee_amount([{'name':'NEW-NAME','price':'43'}],extra),43)
        self.assertEqual(saved_fee_amount([],extra),0)
        self.assertIsNone(saved_fee_amount([{'extra_id':7,'price':'invalid'}],extra))


class PriceValidationTests(TestCase):
    def setUp(self):
        starting_data.RecurringQuoteTests.setUp(self)
        self.client.force_login(get_user_model().objects.create_user(username='price-review'))
        self.quote.driver_count = 1
        self.quote.return_datetime = self.quote.return_datetime.replace(hour=7)
        self.quote.save()
        self.extra = SupplierExtra.objects.create(supplier=self.supplier,extra_code='OUT_OF_HOURS',name='TEST-NIGHT')
        self.night_rate = SupplierExtraRate.objects.create(extra=self.extra,amount_gross=43,calculation_type='PER_UNIT',valid_from=date(2026,1,1))
        self.option = QuoteOption.objects.create(quote=self.quote,supplier=self.supplier,vehicle_group=self.group,
            comparison_class=self.comparison,total_price_gross=400,supplier_name_snapshot='Test',
            vehicle_group_name_snapshot='Test group',calculation_snapshot={'base':'400','extras_total':'0','lines':[]})

    def test_stale_offer_cannot_be_previewed_copied_edited_or_sent(self):
        original = dict(self.option.calculation_snapshot)
        with patch('quotes.views.EmailMultiAlternatives.send') as send:
            for route in ('quote_preview','copy_quote','email_editor','send_quote'):
                with self.subTest(route=route):
                    method = self.client.post if route=='send_quote' else self.client.get
                    response=method(reverse('quotes:'+route,args=[self.quote.quote_number]))
                    self.assertEqual(response.status_code,409)
            send.assert_not_called()
        self.option.refresh_from_db()
        self.assertEqual(self.option.calculation_snapshot,original)
        self.assertEqual(self.option.total_price_gross,400)

    def test_recalculation_preserves_manual_fee_and_unblocks_export(self):
        self.option.manual_adjustment_label='TEST-MANUAL'
        self.option.manual_adjustment_amount=Decimal(25)
        self.option.total_price_gross=425
        self.option.save()
        url=reverse('quotes:calculate_quote',args=[self.quote.quote_number])
        page=self.client.get(url)
        option=page.context['options'][0]
        self.assertTrue(option['was_selected'])
        self.assertEqual(option['manual_amount'],25)
        self.assertEqual(option['total'],443)
        response=self.client.post(url,{'selected_options':[self.group.pk],f'manual_label_{self.group.pk}':'TEST-MANUAL',f'manual_amount_{self.group.pk}':'25'})
        self.assertEqual(response.status_code,302)
        self.option.refresh_from_db()
        self.assertEqual(self.option.total_price_gross,468)
        self.assertEqual(quote_price_issues(self.quote),[])
        self.assertEqual(self.client.get(reverse('quotes:copy_quote',args=[self.quote.quote_number])).status_code,200)

    def test_fee_in_text_but_missing_from_total_is_blocked(self):
        self.option.calculation_snapshot={'base':'400','extras_total':'0','lines':[{'extra_id':self.extra.pk,'price':'43'}]}
        self.option.save()
        self.assertTrue(quote_price_issues(self.quote))

    def test_return_at_start_of_working_hours_needs_no_fee(self):
        self.quote.return_datetime = self.quote.return_datetime.replace(hour=8)
        self.quote.save()
        self.assertEqual(quote_price_issues(self.quote), [])

    def test_recalculated_offer_can_be_sent(self):
        self.client.post(reverse('quotes:calculate_quote',args=[self.quote.quote_number]),
                         {'selected_options':[self.group.pk]})
        with patch('quotes.views.EmailMultiAlternatives.send', return_value=1) as send:
            response=self.client.post(reverse('quotes:send_quote',args=[self.quote.quote_number]))
            self.assertEqual(response.status_code,302)
            send.assert_called_once()
        self.option.refresh_from_db()
        self.assertEqual(self.option.total_price_gross,443)

    def test_missing_rate_and_wrong_event_quantity_are_blocked(self):
        self.night_rate.is_active=False
        self.night_rate.save()
        self.assertIn('нет действующего тарифа',quote_price_issues(self.quote)[0])
        self.night_rate.is_active=True
        self.night_rate.save()
        self.quote.pickup_datetime=self.quote.pickup_datetime.replace(hour=7)
        self.quote.save()
        self.option.calculation_snapshot={'base':'400','extras_total':'43','lines':[{'extra_id':self.extra.pk,'price':'43'}]}
        self.option.total_price_gross=443
        self.option.save()
        self.assertIn('86.00',quote_price_issues(self.quote)[0])
