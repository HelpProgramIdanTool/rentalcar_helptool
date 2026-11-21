"""Configured local rental modes reuse the ordinary quote workflow."""
from django import forms
from django.utils.translation import gettext_lazy as _
from suppliers.models import SupplierLocalBranch, OfferCity
from .country_rules import country_code


class LocalRentalModeField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.offer_mode_label or f'{obj.supplier} — {obj.country}'


def mode_choices():
    return SupplierLocalBranch.objects.filter(offer_mode_enabled=True, country__is_active=True,
        city__is_active=True, supplier__status='ACTIVE').select_related('supplier','city','country')


def configure_modes(form):
    modes = list(mode_choices())
    form.fields['local_rental_branch'].queryset = mode_choices()
    form.local_mode_data = {str(mode.pk): {
        'supplier': str(mode.supplier_id), 'country': mode.country.code,
        'city': mode.city.name, 'help': mode.offer_mode_help,
        'cities': [city.name for city in OfferCity.objects.filter(is_active=True)
                   if country_code(city.country) == mode.country.code],
        'cross_border_label': str(_('Выезд за пределы страны аренды')) + ': ' + mode.country.name,
    } for mode in modes}


def validate_mode(cleaned, add_error):
    mode = cleaned.get('local_rental_branch')
    if not mode:
        return
    cleaned['rental_country'] = mode.country.code
    if not mode.offer_mode_pricing_confirmed:
        add_error('local_rental_branch', _('Тарифы местной аренды ещё не подтверждены. Расчёт заблокирован до проверки условий.'))
    for side in ('pickup', 'return'):
        city = cleaned.get(side+'_city', '')
        if city and country_code_for_city(city) != mode.country.code:
            add_error(side+'_city', _('Местная аренда требует получения и возврата в одной стране. Для международного маршрута переключитесь в обычный режим; данные сохранятся.'))
    suppliers, groups = cleaned.get('suppliers'), cleaned.get('vehicle_groups')
    if suppliers is not None and (not suppliers.exists() or suppliers.exclude(pk=mode.supplier_id).exists()):
        add_error('suppliers', _('В этом режиме доступна только фирма местного отделения.'))
    if groups is not None and groups.exclude(supplier_id=mode.supplier_id).exists():
        add_error('vehicle_groups', _('Выберите группы фирмы местного отделения.'))


def country_code_for_city(city):
    from .country_rules import location_country
    return location_country(city)
