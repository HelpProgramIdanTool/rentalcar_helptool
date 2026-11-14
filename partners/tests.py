from datetime import timedelta
from decimal import Decimal
from smtplib import SMTPException
from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from suppliers.models import Supplier, VehicleGroup, VehicleModel, VehicleComparisonClass, FormVehicleCategory, OfferCity, PriceList, PriceSeason, PriceDayRange, VehicleRate
from quotes.models import Quote, QuoteEmailDelivery
from quotes.services import calculate_quote_options
from .forms import RecipientForm
from .models import PartnerAccess, PartnerDraft, PortalConfiguration, SupplierSummary, PartnerDelivery
from .services import automatic_allowed, complete_option, trip_quote, calculate_options


class EligibilityTests(SimpleTestCase):
    def test_portal_dates_accept_dotted_format_and_reject_impossible_dates(self):
        from datetime import date
        from .forms import TripForm
        from .templatetags.partner_dates import portal_date
        field=TripForm.base_fields['pickup_date']
        self.assertEqual(field.clean('01.12.2026'),date(2026,12,1))
        self.assertIn('01.12.2026',field.widget.render('pickup_date',date(2026,12,1)))
        with self.assertRaises(ValidationError):
            field.clean('31.02.2027')
        self.assertEqual(portal_date('2026-12-01'),'01.12.2026')

    def test_each_changed_declaration_requires_manual_review(self):
        data = dict(driver_ok=True,credit_ok=True,border_ok=True,foreign_route=False)
        self.assertTrue(automatic_allowed(data))
        for key in ('driver_ok','credit_ok','border_ok'):
            self.assertFalse(automatic_allowed({**data,key:False}))
        self.assertFalse(automatic_allowed({**data,'foreign_route':True}))

    def test_partial_prices_and_missing_border_fee_are_not_offers(self):
        row = dict(available=True,unavailable_requests=[],extra_lines=[])
        self.assertTrue(complete_option(row))
        self.assertFalse(complete_option(row,True))
        self.assertFalse(complete_option({**row,'extra_lines':[{'warning':'TEST-MISSING-RATE'}]}))
        self.assertFalse(complete_option({**row,'unavailable_requests':['GPS']}))
        self.assertTrue(complete_option({**row,'extra_lines':[{'extra':SimpleNamespace(extra_code='CROSS_BORDER')} ]},True))

    def test_client_email_is_only_required_for_explicit_client_copy(self):
        data=dict(customer_name='TEST-NAME',partner_email='partner@example.invalid',checked=True)
        self.assertTrue(RecipientForm(data).is_valid())
        self.assertFalse(RecipientForm({**data,'send_customer':True}).is_valid())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PartnerFlowTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='TEST-PARTNER',password='TEST-PASS')
        self.partner=PartnerAccess.objects.create(user=self.user,display_name='TEST-PARTNER-HE',email='partner@example.invalid')
        self.other_user=get_user_model().objects.create_user(username='OTHER',password='TEST-PASS')
        self.other=PartnerAccess.objects.create(user=self.other_user,display_name='OTHER-PARTNER',email='other@example.invalid')
        config=PortalConfiguration.objects.first()
        config.owner_email='owner@example.invalid'
        config.save()
        self.supplier=Supplier.objects.create(supplier_code='TEST-PORTAL',supplier_name='TEST-SUPPLIER')
        self.group=VehicleGroup.objects.create(supplier=self.supplier,group_code='TEST-SUV',group_name='TEST-GROUP',customer_name_he='TEST-GROUP-HE',show_in_offers=True)
        comparison=VehicleComparisonClass.objects.create(code='TEST-PORTAL',name='TEST-COMPARISON')
        self.group.comparison_classes.add(comparison)
        category=FormVehicleCategory.objects.create(name='TEST-CATEGORY-HE')
        category.vehicle_groups.add(self.group)
        OfferCity.objects.update_or_create(name='TEST-CITY',defaults={'label':'TEST-CITY-HE','country':'Poland','cross_border_required':False})
        self.pickup=(timezone.localtime()+timedelta(days=10)).replace(hour=10,minute=0,second=0,microsecond=0)
        price=PriceList.objects.create(supplier=self.supplier,name='TEST-PRICE',version='TEST',effective_from=self.pickup.date()-timedelta(days=1),status='ACTIVE')
        season=PriceSeason.objects.create(price_list=price,season_code='TEST',season_name='TEST',rental_date_from=self.pickup.date()-timedelta(days=1))
        band=PriceDayRange.objects.create(price_list=price,range_code='TEST',label='TEST',days_from=1)
        self.rate=VehicleRate.objects.create(season=season,day_range=band,vehicle_group=self.group,daily_rate_gross=100)
        self.client.force_login(self.user)

    def trip_data(self,**changes):
        data=dict(driver_ok='on',credit_ok='on',border_ok='on',pickup_date=self.pickup.date().isoformat(),pickup_time='10:00',return_date=(self.pickup+timedelta(days=3)).date().isoformat(),return_time='10:00',pickup_city='TEST-CITY',return_city='TEST-CITY',pickup_service='AIRPORT',return_service='AIRPORT',drivers=1,seats=0)
        return {**data,**changes}

    def draft(self):
        response=self.client.post(reverse('partners:trip'),self.trip_data())
        self.assertEqual(response.status_code,302)
        return PartnerDraft.objects.filter(partner=self.partner).latest('created_at')

    def ready(self,customer_copy=False):
        draft=self.draft()
        response=self.client.post(reverse('partners:options',args=[draft.pk]),{'groups':[self.group.pk]})
        self.assertEqual(response.status_code,302)
        response=self.client.post(reverse('partners:review',args=[draft.pk]),dict(customer_name='TEST-CLIENT',partner_email=self.partner.email,customer_email='client@example.invalid',send_customer='on' if customer_copy else '',checked='on'))
        self.assertEqual(response.status_code,302)
        draft.refresh_from_db()
        return draft

    def test_partner_cannot_open_operator_pages_or_another_tenant(self):
        for path in ['/','/customers/','/bookings/','/admin/','/offer-price-preview/']:
            self.assertEqual(self.client.get(path).status_code,403,path)
        draft=PartnerDraft.objects.create(partner=self.other)
        for action in ('options','review','preview','send'):
            self.assertEqual(self.client.post(reverse('partners:'+action,args=[draft.pk])).status_code,404)

    def test_history_does_not_show_other_partner(self):
        PartnerDraft.objects.create(partner=self.other,manual_message='OTHER-PRIVATE-REQUEST')
        self.assertNotContains(self.client.get(reverse('partners:home')),'OTHER-PRIVATE-REQUEST')

    def test_declarations_start_checked_and_reversed_dates_have_visible_error(self):
        response=self.client.get(reverse('partners:trip'))
        for field in ('driver_ok','credit_ok','border_ok'):
            self.assertTrue(response.context['form'][field].value())
        response=self.client.post(reverse('partners:trip'),self.trip_data(return_date=(self.pickup-timedelta(days=1)).date().isoformat()))
        self.assertContains(response,'ההחזרה חייבת להיות אחרי הקבלה.')
        self.assertFalse(PartnerDraft.objects.exists())

    def test_customer_visible_copy_comes_from_configured_data(self):
        config=PortalConfiguration.objects.first();config.content={'common':['TEST-BENEFIT-HE']};config.save()
        summary=SupplierSummary.objects.first();summary.facts={'fuel':'TEST-FUEL-HE'};summary.save()
        response=self.client.get(reverse('partners:home'))
        self.assertContains(response,'TEST-BENEFIT-HE')
        self.assertContains(response,'TEST-FUEL-HE')

    def test_same_calculator_and_round_invented_price(self):
        VehicleModel.objects.create(vehicle_group=self.group,brand='TEST-BRAND',model='TEST-MODEL')
        VehicleModel.objects.create(vehicle_group=self.group,brand='HIDDEN-BRAND',model='HIDDEN-MODEL',is_active=False)
        draft=self.draft()
        portal=calculate_options(draft.trip,[self.group])[self.group.pk]
        manual=calculate_quote_options(trip_quote(draft.trip),vehicle_group=self.group)[0]
        self.assertEqual(portal['total'],Decimal('300'))
        self.assertEqual(portal['total'],manual['total'])
        response=self.client.get(reverse('partners:options',args=[draft.pk]))
        self.assertContains(response,'TEST-GROUP-HE')
        self.assertContains(response,'TEST-CATEGORY-HE')
        self.assertContains(response,'TEST-BRAND TEST-MODEL')
        self.assertNotContains(response,'HIDDEN-MODEL')

    def test_unchecked_declaration_is_saved_and_routed_to_manual_without_quote(self):
        response=self.client.post(reverse('partners:trip'),self.trip_data(driver_ok=''))
        self.assertContains(response,'בדיקה אישית')
        self.assertEqual(PartnerDraft.objects.count(),1)
        self.assertFalse(Quote.objects.exists())

    def test_client_is_not_emailed_without_opt_in_and_retry_is_idempotent(self):
        draft=self.ready()
        self.assertEqual(draft.quote.options.get().total_price_gross,Decimal('300'))
        self.assertEqual(draft.quote.language,'Hebrew')
        self.assertEqual(self.client.get(reverse('partners:preview',args=[draft.pk]))['X-Frame-Options'],'SAMEORIGIN')
        response=self.client.post(reverse('partners:send',args=[draft.pk]))
        self.assertEqual(response.status_code,302)
        self.assertEqual({r for msg in mail.outbox for r in msg.to},{'partner@example.invalid','owner@example.invalid'})
        self.client.post(reverse('partners:send',args=[draft.pk]))
        self.assertEqual(len(mail.outbox),2)
        self.assertEqual(QuoteEmailDelivery.objects.count(),2)
        self.assertIn('הצעת מחיר',mail.outbox[0].subject)
        self.assertIn('מחיר כולל',mail.outbox[0].body)
        self.assertIn('dir="rtl"',mail.outbox[0].alternatives[0].content)
        self.assertNotIn('Price includes',mail.outbox[0].alternatives[0].content)

    def test_client_opt_in_and_failed_recipient_retry(self):
        draft=self.ready(customer_copy=True)
        from django.core.mail.message import EmailMultiAlternatives
        original=EmailMultiAlternatives.send
        def send_except_owner(msg,**kwargs):
            if msg.to==['owner@example.invalid']:
                raise SMTPException('TEST-FAIL')
            return original(msg,**kwargs)
        with patch.object(EmailMultiAlternatives,'send',send_except_owner):
            self.client.post(reverse('partners:send',args=[draft.pk]))
        self.assertEqual(len(mail.outbox),2)
        self.assertEqual(PartnerDelivery.objects.filter(sent_at__isnull=True).count(),1)
        self.client.post(reverse('partners:send',args=[draft.pk]))
        self.assertEqual(len(mail.outbox),3)
        self.assertEqual(mail.outbox[-1].to,['owner@example.invalid'])

    def test_stale_prices_are_blocked_and_not_emailed(self):
        draft=self.ready()
        self.rate.daily_rate_gross=200;self.rate.save()
        self.client.post(reverse('partners:send',args=[draft.pk]))
        self.assertFalse(PartnerDelivery.objects.exists())
        self.assertEqual(len(mail.outbox),0)

    def test_repeated_prepare_does_not_duplicate_customer_or_quote(self):
        draft=self.ready()
        original=draft.quote_id
        self.client.post(reverse('partners:review',args=[draft.pk]),{'customer_name':'DIFFERENT'})
        draft.refresh_from_db()
        self.assertEqual(draft.quote_id,original)
        self.assertEqual(Quote.objects.count(),1)

    def test_manual_request_carries_trip_without_sending_a_quote(self):
        draft=self.draft()
        self.client.post(reverse('partners:manual'),{'draft':draft.pk,'message':'TEST-MANUAL'})
        draft.refresh_from_db()
        self.assertTrue(draft.manual_requested)
        self.assertIn('TEST-CITY',mail.outbox[0].body)
        self.assertFalse(Quote.objects.exists())

    def test_deactivated_partner_can_logout_but_cannot_open_data(self):
        self.partner.is_active=False;self.partner.save()
        self.assertEqual(self.client.get(reverse('partners:home')).status_code,403)
        self.assertEqual(self.client.post(reverse('partners:logout')).status_code,302)

    def test_login_only_accepts_partner_and_ignores_operator_next(self):
        self.client.logout()
        response=self.client.post(reverse('partners:login')+'?next=/customers/',{'username':'TEST-PARTNER','password':'TEST-PASS'})
        self.assertRedirects(response,reverse('partners:home'))
        self.client.logout()
        outsider=get_user_model().objects.create_user(username='NO-PORTAL',password='TEST-PASS')
        response=self.client.post(reverse('partners:login'),{'username':outsider.username,'password':'TEST-PASS'})
        self.assertEqual(response.status_code,200)
        self.assertIn('__all__',response.context['form'].errors)

    def test_mail_recipients_remain_the_ones_reviewed(self):
        draft=self.ready()
        config=PortalConfiguration.objects.first();config.owner_email='changed@example.invalid';config.save()
        self.client.post(reverse('partners:send',args=[draft.pk]))
        recipients={r for msg in mail.outbox for r in msg.to}
        self.assertIn('owner@example.invalid',recipients)
        self.assertNotIn('changed@example.invalid',recipients)

    def test_group_not_in_configured_categories_cannot_be_injected(self):
        draft=self.draft()
        group=VehicleGroup.objects.create(supplier=self.supplier,group_code='HIDDEN',group_name='HIDDEN',show_in_offers=True)
        self.client.post(reverse('partners:options',args=[draft.pk]),{'groups':[group.pk]})
        draft.refresh_from_db()
        self.assertEqual(draft.selected_groups,[])

    def test_invalid_manual_draft_identifier_is_not_a_server_error(self):
        self.assertEqual(self.client.post(reverse('partners:manual'),{'draft':'invalid','message':'TEST'}).status_code,400)

    def test_suspended_group_is_unavailable_in_portal_and_shared_calculator(self):
        from .services import available_groups
        draft=self.draft()
        self.group.is_active=False;self.group.show_in_offers=False;self.group.save()
        self.assertNotIn(self.group,available_groups())
        self.assertEqual(calculate_quote_options(trip_quote(draft.trip),vehicle_group=self.group),[])
        self.client.post(reverse('partners:options',args=[draft.pk]),{'groups':[self.group.pk]})
        draft.refresh_from_db()
        self.assertEqual(draft.selected_groups,[])

    @override_settings(PARTNER_LOGIN_MAX_FAILURES=2)
    def test_failed_login_limit_uses_shared_database(self):
        self.client.logout()
        url=reverse('partners:login')
        for _ in range(2):
            self.assertEqual(self.client.post(url,{'username':'TEST-PARTNER','password':'WRONG'}).status_code,200)
        self.assertEqual(self.client.post(url,{'username':'TEST-PARTNER','password':'TEST-PASS'}).status_code,429)
