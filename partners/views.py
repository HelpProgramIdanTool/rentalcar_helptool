import base64
import hashlib
from datetime import timedelta
from functools import wraps
from uuid import UUID
from smtplib import SMTPException
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from quotes.email_tools import seat_guides
from quotes.localization import offer_subject
from quotes.models import Quote, QuoteEmailDelivery
from quotes.views import _quote_preview_context
from .forms import PartnerLoginForm, TripForm, RecipientForm
from .models import PartnerAccess, PortalConfiguration, SupplierSummary, PartnerDraft, PartnerDelivery, PartnerLoginAttempt
from .services import automatic_allowed, calculate_options, categories_with_options, prepare_quote, stale_quote


class PartnerLogin(LoginView):
    template_name = 'partners/login.html'
    authentication_form = PartnerLoginForm
    next_page = reverse_lazy('partners:home')
    redirect_authenticated_user = False

    def attempt_keys(self):
        username = self.request.POST.get('username','').strip().casefold()
        ip = self.request.META.get('REMOTE_ADDR','unknown')
        return (salted_hmac('partner-login-user',username,algorithm='sha256').hexdigest(),
                salted_hmac('partner-login-ip',ip,algorithm='sha256').hexdigest())

    def post(self, request, *args, **kwargs):
        user_key, ip_key = self.attempt_keys()
        recent = PartnerLoginAttempt.objects.filter(created_at__gte=timezone.now()-timedelta(minutes=15))
        if (recent.filter(username_key=user_key).count() >= getattr(settings,'PARTNER_LOGIN_MAX_FAILURES',10)
                or recent.filter(ip_key=ip_key).count() >= 50):
            return render(request,self.template_name,{'form':PartnerLoginForm(request=request),'rate_limited':True},status=429)
        return super().post(request,*args,**kwargs)

    def form_invalid(self, form):
        user_key, ip_key = self.attempt_keys()
        PartnerLoginAttempt.objects.create(username_key=user_key,ip_key=ip_key)
        return super().form_invalid(form)

    def form_valid(self, form):
        user_key, _ = self.attempt_keys()
        PartnerLoginAttempt.objects.filter(username_key=user_key).delete()
        return super().form_valid(form)

    def get_success_url(self):
        # Never accept ?next= an operator page for a partner session.
        return str(self.next_page)


def partner_only(view):
    @wraps(view)
    @never_cache
    def checked(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('partners:login')
        request.partner = PartnerAccess.objects.filter(user=request.user, is_active=True).first()
        if not request.partner:
            return HttpResponseForbidden('אין הרשאה לקבינט השותפים.')
        return view(request, *args, **kwargs)
    return checked


def configuration():
    return PortalConfiguration.objects.first()


def context(request, **kwargs):
    config = configuration()
    return {'partner':request.partner, 'copy':config.content if config else {},
        'summaries':SupplierSummary.objects.filter(is_active=True), **kwargs}


def owned(request, pk):
    return get_object_or_404(PartnerDraft.objects.select_related('quote','partner'), pk=pk, partner=request.partner)


@partner_only
def home(request):
    return render(request, 'partners/home.html', context(request,
        drafts=request.partner.drafts.order_by('-created_at')[:30]))


@partner_only
def trip(request):
    form = TripForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        payload = {key:value.isoformat() if hasattr(value,'isoformat') else value for key,value in form.cleaned_data.items()}
        payload['pricing_sub_agent_id'] = request.partner.pricing_sub_agent_id
        draft = PartnerDraft.objects.create(partner=request.partner, trip=payload)
        if not automatic_allowed(payload):
            messages.warning(request, 'הנתונים דורשים בדיקה אישית של עידן. כל הפרטים נשמרו; אפשר להעביר אותם אליו כאן.')
            return render(request, 'partners/manual.html', context(request, draft=draft))
        return redirect('partners:options', pk=draft.pk)
    return render(request, 'partners/trip.html', context(request, form=form))


@partner_only
def options(request, pk):
    draft = owned(request, pk)
    if draft.quote_id:
        return redirect('partners:review', pk=pk)
    if not automatic_allowed(draft.trip):
        return render(request, 'partners/manual.html', context(request,draft=draft))
    try:
        results = calculate_options(draft.trip)
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect('partners:trip')
    if request.method == 'POST':
        try:
            ids = set(map(int,request.POST.getlist('groups')))
        except (ValueError, TypeError):
            ids = set()
        if not ids or any(not results.get(pk) for pk in ids):
            messages.error(request, 'נא לבחור לפחות אפשרות אחת עם מחיר מלא.')
        else:
            draft.selected_groups = sorted(ids)
            draft.save(update_fields=['selected_groups','updated_at'])
            return redirect('partners:review', pk=draft.pk)
    return render(request, 'partners/options.html', context(request,draft=draft,categories=categories_with_options(results)))


@partner_only
def review(request, pk):
    draft = owned(request, pk)
    config = configuration()
    if request.method == 'POST' and not draft.quote_id:
        form = RecipientForm(request.POST)
        if form.is_valid():
            if not config or not config.owner_email:
                messages.error(request, 'כתובת עידן עדיין לא הוגדרה. נא לפנות אליו.')
            else:
                try:
                    with transaction.atomic():
                        draft = PartnerDraft.objects.select_for_update().get(pk=pk, partner=request.partner)
                        if not draft.quote_id:
                            prepare_quote(draft,form.cleaned_data,config,request.user)
                    return redirect('partners:review',pk=pk)
                except ValidationError as error:
                    messages.error(request,error.messages[0])
    else:
        form = RecipientForm(initial={'partner_email':request.partner.email})
    recipient = draft.trip.get('recipient',{})
    addresses = list(dict.fromkeys(filter(None,[recipient.get('partner_email'), recipient.get('owner_email'), recipient.get('customer_email') if recipient.get('send_customer') else ''])))
    return render(request, 'partners/review.html', context(request,draft=draft,form=form,addresses=addresses,deliveries=draft.deliveries.all()))


@partner_only
@xframe_options_sameorigin
def preview(request, pk):
    draft = owned(request, pk)
    if not draft.quote_id:
        return HttpResponse(status=404)
    html = draft.delivery_html or render_to_string('quotes/quote_preview.html',_quote_preview_context(draft.quote,is_email=True))
    response = HttpResponse(html)
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; frame-ancestors 'self'"
    return response


@partner_only
@require_POST
def send(request, pk):
    with transaction.atomic():
        draft = get_object_or_404(PartnerDraft.objects.select_for_update().select_related('quote','partner'),pk=pk,partner=request.partner)
        config = configuration()
        if not draft.quote_id or not config or not config.owner_email:
            return HttpResponse(status=409)
        if draft.deliveries.exists() and not draft.deliveries.filter(sent_at__isnull=True).exists():
            messages.success(request, 'ההצעה כבר נשלחה לכל הנמענים. לא נשלחו עותקים נוספים.')
            return redirect('partners:review',pk=pk)
        if not draft.delivery_html:
            try:
                if stale_quote(draft):
                    raise ValidationError('המחירים השתנו. יש לפנות לעידן לפני שליחה.')
            except ValidationError as error:
                messages.error(request,error.messages[0])
                return redirect('partners:review',pk=pk)
            ctx = _quote_preview_context(draft.quote,is_email=True)
            draft.delivery_html = render_to_string('quotes/quote_preview.html',ctx)
            draft.delivery_text = render_to_string('quotes/quote_email.txt',ctx)
            draft.delivery_subject = config.content.get('offer_subject_prefix','הצעת מחיר להשכרת רכב') + ' · ' + draft.quote.quote_number
            recipient = draft.trip['recipient']
            addresses = {recipient['partner_email'].strip().casefold(), recipient['owner_email'].strip().casefold()}
            if recipient['send_customer']:
                addresses.add(recipient['customer_email'].strip().casefold())
            for address in addresses:
                PartnerDelivery.objects.get_or_create(draft=draft, recipient=address)
            draft.save(update_fields=['delivery_html','delivery_text','delivery_subject','updated_at'])
        # Separate messages prevent disclosing the other recipients to the client.
        for delivery in draft.deliveries.filter(sent_at__isnull=True):
            message = EmailMultiAlternatives(subject=draft.delivery_subject, body=draft.delivery_text or 'הצעה '+draft.quote.quote_number,
                to=[delivery.recipient],alternatives=[(draft.delivery_html,'text/html')])
            attachments = []
            try:
                for guide in seat_guides(draft.quote):
                    content = guide['path'].read_bytes()
                    message.attach(guide['filename'],content,'application/pdf')
                    attachments.append({'filename':guide['filename'],'sha256':hashlib.sha256(content).hexdigest(),'data':base64.b64encode(content).decode('ascii')})
                if message.send(fail_silently=False) != 1:
                    raise SMTPException('Mail was not accepted')
            except (SMTPException, OSError):
                delivery.error = 'השליחה נכשלה. אפשר לנסות שוב; עותקים שכבר נשלחו לא יישלחו שוב.'
            else:
                delivery.sent_at = timezone.now()
                delivery.error = ''
                QuoteEmailDelivery.objects.create(quote=draft.quote,sent_by_user=request.user,recipient=delivery.recipient,
                    subject=draft.delivery_subject,html=draft.delivery_html,attachments=attachments)
            delivery.save(update_fields=['sent_at','error'])
        if not draft.deliveries.filter(sent_at__isnull=True).exists():
            draft.quote.status = Quote.Status.SENT
            draft.quote.sent_at = timezone.now()
            draft.quote.sent_by_user = request.user
            draft.quote.sent_html_snapshot = draft.delivery_html
            draft.quote.sent_to_email = draft.trip['recipient']['partner_email']
            draft.quote.sent_subject = draft.delivery_subject
            draft.quote.save(update_fields=['status','sent_at','sent_by_user','sent_html_snapshot','sent_to_email','sent_subject'])
            messages.success(request, 'ההצעה נשלחה בהצלחה. אפשר לראות את תוצאות השליחה למטה.')
        else:
            messages.error(request, 'לא כל העותקים נשלחו. הפרטים נשמרו ואפשר לנסות שוב.')
    return redirect('partners:review',pk=pk)


@partner_only
def manual(request):
    if request.method == 'POST':
        message = request.POST.get('message','').strip()[:3000]
        if not message:
            messages.error(request,'נא לתאר בקצרה מה צריך לבדוק.')
            return render(request,'partners/manual.html',context(request))
        with transaction.atomic():
            pk = request.POST.get('draft')
            if pk:
                try:
                    UUID(pk)
                except (ValueError, TypeError):
                    return HttpResponse(status=400)
            draft = owned(request,pk) if pk else PartnerDraft.objects.create(partner=request.partner,
                trip={key:request.POST.get(key,'') for key in TripForm.base_fields if key in request.POST})
            draft = PartnerDraft.objects.select_for_update().get(pk=draft.pk)
            if not draft.manual_requested:
                draft.manual_requested = True
                draft.manual_message = message
                draft.save(update_fields=['manual_requested','manual_message','updated_at'])
                config = configuration()
                if config and config.owner_email:
                    body = f'Partner: {request.partner.display_name}\nDraft: {draft.pk}\n{message}\n\n{draft.trip}'
                    try:
                        if send_mail('Partner portal: manual calculation',body,None,[config.owner_email],fail_silently=False) != 1:
                            raise SMTPException('Mail not accepted')
                    except (SMTPException,OSError):
                        messages.warning(request,'הבקשה נשמרה לעידן במערכת, אך הודעת הדוא״ל לא נשלחה. נא ליצור קשר ישירות.')
                    else:
                        messages.success(request,'הבקשה הועברה לעידן עם הפרטים שכבר מילאתם.')
                else:
                    messages.warning(request,'הבקשה נשמרה לעידן במערכת. כתובת ההתראה עדיין לא הוגדרה.')
        return redirect('partners:home')
    return render(request,'partners/manual.html',context(request))
