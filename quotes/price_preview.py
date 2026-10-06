"""Read-only prices beside vehicle choices, using the final quote calculator."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from config.rental_duration import calculate_rental_days
from suppliers.models import VehicleGroup, Supplier
from .forms import FirstInquiryForm
from .models import Quote
from .services import calculate_quote_options


@login_required
@require_POST
@never_cache
def preview_prices(request):
    form = FirstInquiryForm(request.POST, pricing_only=True)
    if not form.is_valid():
        return JsonResponse({'prices': {}, 'errors': form.errors.get_json_data()}, status=400)
    data = form.cleaned_data
    quote = Quote(**{key: data[key] for key in (
        'pickup_datetime', 'return_datetime', 'pickup_city', 'return_city',
        'pickup_service', 'return_service', 'pickup_address', 'return_address',
        'driver_count', 'cross_border_requested', 'sub_agent',
    )})
    quote.rental_days = calculate_rental_days(quote.pickup_datetime, quote.return_datetime)
    quote.extra_requests = {code: data['child_seat_quantity'] if code == 'CHILD_SEAT'
                           else data['young_driver_quantity'] if code == 'YOUNG_DRIVER' else 1
                           for code in data['extra_choices']}
    groups = VehicleGroup.objects.filter(supplier__in=data['suppliers'],
        supplier__status=Supplier.Status.ACTIVE, is_active=True, show_in_offers=True).select_related('supplier')
    prices = {}
    for group in groups:
        options = calculate_quote_options(quote, vehicle_group=group)
        option = options[0] if options else None
        complete = bool(option and option['available'] and not option['unavailable_requests']
                        and not any(line.get('warning') for line in option['extra_lines']))
        if complete and quote.cross_border_requested:
            complete = any(line['extra'].extra_code == 'CROSS_BORDER' for line in option['extra_lines'])
        prices[str(group.pk)] = ({'available': True, 'total': str(option['total']), 'currency': option['currency']}
            if complete else {'available': False, 'reason': (option.get('reason') if option else '')
                             or 'Нет полного расчёта для выбранных дат, услуг или режима сабагента.'})
    return JsonResponse({'prices': prices, 'days': quote.rental_days})
