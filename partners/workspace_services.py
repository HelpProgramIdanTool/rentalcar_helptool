"""Shared pricing and rendering for isolated test and working partner accounts."""
from datetime import timedelta
from .services import calculate_options, automatic_allowed
from suppliers.models import PriceList
from django.db import transaction


@transaction.atomic
def render_workspace_offer(record, user):
    """Render the operator offer; persist working quotes, roll back test rows."""
    from django.db import transaction
    from django.template.loader import render_to_string
    from .models import PartnerDraft, PortalConfiguration
    from types import SimpleNamespace
    from .services import prepare_quote
    from quotes.views import _quote_preview_context
    if not record.is_test:
        draft=PartnerDraft.objects.create(partner=record.partner,trip=record.trip,
            selected_groups=[int(option['id']) for option in record.options])
        config=PortalConfiguration.objects.first()
        if not config or not config.workspace_copy_email:
            from django.core.exceptions import ValidationError
            raise ValidationError('כתובת העותק לעידן אינה מוגדרת. יש לפנות לעידן.')
        quote=prepare_quote(draft,{'customer_name':record.customer_name,
            'customer_email':record.trip.get('customer_email',''),'partner_email':record.partner.email,
            'owner_email':config.workspace_copy_email,'send_customer':False},config,user)
        quote.customer.phone_1=record.trip.get('customer_phone','')
        quote.customer.save(update_fields=['phone_1'])
        from customers.models import ReferralContact,ReferralEmail
        referred=ReferralEmail.objects.filter(email__iexact=record.partner.email).select_related('contact').first()
        if referred:contact=referred.contact
        else:
            contact=ReferralContact.objects.create(name=record.partner.display_name)
            ReferralEmail.objects.create(contact=contact,email=record.partner.email)
        quote.referral_contact=contact;quote.save(update_fields=['referral_contact'])
        record.draft=draft;record.save(update_fields=['draft','updated_at'])
        saved_options={str(option.vehicle_group_id):option for option in quote.options.all()}
        for item in record.options:
            option=saved_options[item['id']]
            item.update(total=str(option.total_price_gross),currency=option.currency,
                deposit=str(option.deposit_amount),deposit_currency=option.deposit_currency)
        record.save(update_fields=['options','updated_at'])
        context=_quote_preview_context(quote,is_email=True)
        context['guides']=[]
        return render_to_string('quotes/quote_preview.html',context)
    with transaction.atomic():
        draft = PartnerDraft.objects.create(partner=record.partner, trip=record.trip,
            selected_groups=[int(option['id']) for option in record.options])
        quote = prepare_quote(draft, {
            'customer_name': record.customer_name,
            'customer_email': '',
        }, PortalConfiguration.objects.first() or SimpleNamespace(owner_email=''), user)
        # Number belongs to the test record, never to a live quote.
        quote.quote_number = record.number
        context = _quote_preview_context(quote, is_email=True)
        context['guides'] = []
        html = render_to_string('quotes/quote_preview.html', context)
        transaction.set_rollback(True)
    return html


def price_valid(issued_at, now, saved_versions, current_versions):
    return now < issued_at + timedelta(days=7) or saved_versions == current_versions


def versions(supplier_id):
    return list(PriceList.objects.filter(supplier_id=supplier_id,status='ACTIVE').order_by('pk').values_list('pk','version'))


def serialise_trip(cleaned, partner):
    data={key:value.isoformat() if hasattr(value,'isoformat') else value for key,value in cleaned.items()}
    data['pricing_sub_agent_id']=partner.pricing_sub_agent_id
    return data


def workspace_options(trip):
    if not automatic_allowed(trip):
        return [],{}
    results=calculate_options(trip)
    options=[]
    supplier_versions={}
    for pk,row in results.items():
        if not row:continue
        if row.get('total') is None or row.get('deposit_amount') is None:continue
        supplier=row['supplier']; group=row['group']
        options.append(dict(id=str(pk),supplier_id=supplier.pk,supplier=supplier.supplier_name,
            name=group.customer_name_he or group.group_name,models=row['models'] or '',
            total=str(row['total']),currency=row['currency'],deposit=str(row['deposit_amount']),
            deposit_currency=row['deposit_currency'],categories=list(group.form_categories.filter(is_active=True).values_list('name',flat=True))))
        supplier_versions[str(supplier.pk)]=versions(supplier.pk)
    return options,supplier_versions
