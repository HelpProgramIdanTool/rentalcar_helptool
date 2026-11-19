"""Test workspace uses the production quote calculator, with no email transport."""
from datetime import timedelta
from .services import calculate_options, automatic_allowed
from suppliers.models import PriceList


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
