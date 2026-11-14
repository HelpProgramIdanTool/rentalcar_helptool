"""Route eligibility only. Amounts and day bands remain in SupplierExtraRate."""
import unicodedata
from decimal import Decimal
from suppliers.models import OfferCity, SupplierExtra


def normalized(value):
    return ' '.join(unicodedata.normalize('NFC',str(value or '')).casefold().split())


def domestic_different_cities(pickup_city, return_city, pickup_country, return_country):
    poland = {'pl','poland','polska','польша','פולין'}
    return bool(normalized(pickup_city) and normalized(return_city)
        and normalized(pickup_city) != normalized(return_city)
        and normalized(pickup_country) in poland and normalized(return_country) in poland)


def automatic_route_extras(quote, supplier):
    extras=list(supplier.extras.filter(is_active=True,automatic_rule=SupplierExtra.AutomaticRule.DOMESTIC_ONE_WAY))
    if not extras or normalized(quote.pickup_city) == normalized(quote.return_city):
        return {}, []
    cities={}
    for side in ('pickup','return'):
        cities[side]=OfferCity.objects.filter(name__iexact=getattr(quote,side+'_city').strip(),is_active=True).first()
    # A known foreign endpoint makes this a non-domestic route, even if the other
    # endpoint is free text. A different foreign fee must be configured separately.
    poland={'pl','poland','polska','польша','פולין'}
    if any(city and normalized(city.country) and normalized(city.country) not in poland for city in cities.values()):
        return {}, []
    if any(not city or not normalized(city.country) for city in cities.values()):
        return {}, ['Не определена страна города: нельзя проверить обязательную доплату за возврат в другом городе.']
    if domestic_different_cities(quote.pickup_city,quote.return_city,cities['pickup'].country,cities['return'].country):
        return {extra.extra_code:Decimal('1') for extra in extras}, []
    return {}, []
