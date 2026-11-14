from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from quotes.forms import QUOTE_STATUS_LABELS
from .models import Customer, ReferralContact, ReferralEmail


class ContactForm(forms.Form):
    name = forms.CharField(label=_('Имя / название'), max_length=200)
    emails = forms.CharField(label=_('Email (по одному на строку)'), widget=forms.Textarea)

    def clean_emails(self):
        values = sorted(set(v.strip().lower() for v in self.cleaned_data['emails'].splitlines() if v.strip()))
        validator = forms.EmailField()
        return [validator.clean(value) for value in values]


class ContactPeriod(forms.Form):
    start = forms.DateField(required=False, label=_('Создано с'), widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(required=False, label=_('Создано до'), widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError(_('Дата начала позже даты окончания.'))
        return data

    def apply(self, queryset):
        if not self.is_valid():
            return queryset.none()
        if self.is_valid():
            if self.cleaned_data['start']:
                queryset = queryset.filter(created_at__date__gte=self.cleaned_data['start'])
            if self.cleaned_data['end']:
                queryset = queryset.filter(created_at__date__lte=self.cleaned_data['end'])
        return queryset


@login_required
def contact_list(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            contact = ReferralContact.objects.create(name=form.cleaned_data['name'])
            for email in form.cleaned_data['emails']:
                ReferralEmail.objects.create(contact=contact, email=email)
        return redirect('customers:contact_detail', contact_id=contact.pk)
    search = request.GET.get('q', '').strip()[:200]
    period = ContactPeriod(request.GET)
    contacts = ReferralContact.objects.filter(Q(name__icontains=search) | Q(emails__email__icontains=search)).distinct()
    rows = []
    for contact in contacts:
        from bookings.models import Booking
        bookings = period.apply(Booking.all_objects.filter(referral_contact=contact))
        rows.append({'contact': contact, 'offers': period.apply(contact.quotes.all()).count(),
                     'bookings': bookings.exclude(status='CANCELLED').count(),
                     'cancelled': bookings.filter(status='CANCELLED').count()})
    return render(request, 'customers/contacts.html', dict(rows=rows, form=form, period=period,
        search=search, query=request.GET.urlencode(), active_menu='customers'))


@login_required
def contact_detail(request, contact_id):
    from bookings.models import Booking
    contact = get_object_or_404(ReferralContact, pk=contact_id)
    period = ContactPeriod(request.GET)
    emails = list(contact.emails.values_list('email', flat=True))
    candidates = Booking.objects.none()
    if request.GET.get('link') == '1' or request.POST.get('action') == 'link':
        match = Q(pk__in=[])
        for email in emails:
            match |= Q(customer_email_snapshot__iexact=email) | Q(customer__email__iexact=email)
        candidates = Booking.all_objects.filter(match, referral_contact__isnull=True).distinct()
    if request.method == 'POST' and request.POST.get('action') == 'link' and request.POST.get('confirm') == 'yes':
        with transaction.atomic():
            candidates.filter(pk__in=[v for v in request.POST.getlist('selected') if v.isdigit()]).update(referral_contact=contact)
        return redirect('customers:contact_detail', contact_id=contact.pk)
    kind = request.GET.get('kind', 'offers')
    if kind == 'offers':
        records = period.apply(contact.quotes.all())
    else:
        records = period.apply(Booking.all_objects.filter(referral_contact=contact))
        records = records.filter(status='CANCELLED') if kind == 'cancelled' else records.exclude(status='CANCELLED')
    return render(request, 'customers/contact_detail.html', dict(contact=contact, records=records,
        kind=kind, candidates=candidates, period=period, active_menu='customers'))


@login_required
def customer_list(request):
    search = request.GET.get("q", "").strip()[:200]
    period = ContactPeriod(request.GET)
    customers = Customer.objects.all()
    for term in search.split():
        customers = customers.filter(
            Q(first_name__icontains=term) | Q(last_name__icontains=term)
            | Q(full_name_latin__icontains=term) | Q(email__icontains=term)
            | Q(phone_1__icontains=term) | Q(phone_2__icontains=term)
            | Q(phone_3__icontains=term)
        )
    page = Paginator(customers.order_by("first_name", "last_name", "pk"), 25).get_page(request.GET.get("page"))
    for customer in page:
        customer.offer_count = period.apply(customer.quotes.all()).count()
        from bookings.models import Booking
        bookings = period.apply(Booking.all_objects.filter(customer=customer))
        customer.booking_count = bookings.exclude(status='CANCELLED').count()
        customer.cancelled_count = bookings.filter(status='CANCELLED').count()
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "customers/list.html", {
        "page_obj": page, "search": search, "filter_query": query.urlencode(),
        "active_menu": "customers", "period": period,
    })


@login_required
def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    period = ContactPeriod(request.GET)
    kind = request.GET.get('kind', 'offers')
    if kind != 'offers':
        from bookings.models import Booking
        records = period.apply(Booking.all_objects.filter(customer=customer))
        records = records.filter(status='CANCELLED') if kind == 'cancelled' else records.exclude(status='CANCELLED')
        return render(request, 'customers/contact_detail.html', dict(contact=customer, records=records,
            kind=kind, period=period, active_menu='customers', customer_mode=True))
    page = Paginator(period.apply(customer.quotes.all()).order_by("-created_at", "-pk"), 25).get_page(request.GET.get("page"))
    for quote in page:
        quote.status_label = QUOTE_STATUS_LABELS.get(quote.status, quote.status)
    return render(request, "customers/detail.html", {
        "customer": customer, "page_obj": page, "active_menu": "customers",
    })
