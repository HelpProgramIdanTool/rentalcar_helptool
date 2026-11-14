"""Country of rental is separate from the country of vehicle handover."""
from suppliers.models import OfferCity, RentalCountry, SupplierLocalBranch


def country_code(value, *, countries=None):
    key=str(value or '').strip().casefold()
    for country in RentalCountry.objects.all() if countries is None else countries:
        if key in {country.code.casefold(),country.name.casefold(),*(str(a).casefold() for a in country.aliases)}:
            return country.code
    return ''


def location_country(city_name):
    city=OfferCity.objects.filter(name__iexact=city_name.strip(),is_active=True).first()
    return country_code(city.country) if city else country_code(city_name.rsplit(',',1)[-1]) if ',' in city_name else ''


def location_country_name(city_name):
    code = location_country(city_name)
    country = RentalCountry.objects.filter(code=code).first() if code else None
    if country:
        return country.name
    city = OfferCity.objects.filter(name__iexact=city_name.strip(), is_active=True).first()
    return city.country if city else city_name.rsplit(',', 1)[-1].strip() if ',' in city_name else ''


def route_flags(base, pickup_country, return_country, declared=False, pickup_waiver=False):
    return {'cross_border':bool(declared or any(c and c!=base for c in (pickup_country,return_country))),
            'prepayment':bool(pickup_country and pickup_country!='PL' and not pickup_waiver)}


def route_context(quote,supplier):
    base=getattr(quote,'rental_country','PL') or 'PL'
    countries={side:location_country(getattr(quote,side+'_city','')) or location_country_name(getattr(quote,side+'_city','')) for side in ('pickup','return')}
    branches=list(SupplierLocalBranch.objects.filter(supplier=supplier).select_related('city','country'))
    pickup=next((b for b in branches if b.city.name.casefold()==quote.pickup_city.strip().casefold()),None)
    flags=route_flags(base,countries['pickup'],countries['return'],quote.cross_border_requested,
        bool(pickup and pickup.waive_prepayment))
    flags['base']=base
    flags['countries']=countries
    flags['unsupported']=base!='PL' and not any(b.country.code==base for b in branches)
    flags['warnings']=[]
    if base != 'PL' and all(value and value != base for value in countries.values()):
        flags['warnings'].append('Страна аренды не совпадает ни со страной получения, ни со страной возврата. Проверьте выбор вручную.')
    for branch in branches:
        if branch.country.code!=base and any(branch.city.name.casefold()==getattr(quote,s+'_city').strip().casefold() for s in ('pickup','return')):
            flags['warnings'].append(f'{supplier.supplier_name}: в городе {branch.city.name} есть местное отделение. Проверьте страну аренды: {branch.country.name}.')
    flags['local_sides']={side for side in ('pickup','return') if any(b.waive_foreign_delivery and b.country.code==base and b.city.name.casefold()==getattr(quote,side+'_city').strip().casefold() for b in branches)}
    country=RentalCountry.objects.filter(code=base).first()
    flags['wording']=country.wording if country else {}
    flags['prepayment_text']=country.prepayment_text if country else {}
    return flags


def localize_country_text(text,quote, *, country=None):
    if country is None:
        country=RentalCountry.objects.filter(code=getattr(quote,'rental_country','PL')).first()
    for original,replacement in sorted((country.wording if country else {}).items(),key=lambda pair:-len(pair[0])):
        text=text.replace(original,replacement)
    return text
