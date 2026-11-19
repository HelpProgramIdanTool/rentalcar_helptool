"""Test workspace uses the production quote calculator, with no email transport."""
from datetime import timedelta
from .services import calculate_options, automatic_allowed
from suppliers.models import PriceList


def render_workspace_offer(record, user):
    """Render the operator's full offer, rolling back all temporary working rows.

    Only the resulting HTML is retained in the separate test workspace record.
    Never send mail or leave test customers/quotes in the operator's database.
    """
    from django.db import transaction
    from django.template.loader import render_to_string
    from .models import PartnerDraft, PortalConfiguration
    from types import SimpleNamespace
    from .services import prepare_quote
    from quotes.views import _quote_preview_context
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
