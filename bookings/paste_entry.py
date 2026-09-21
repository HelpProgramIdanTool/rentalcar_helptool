"""Parse a compact supplier request without creating or sending a booking."""
import html
import re
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from quotes.forms import FirstInquiryForm


def parse_booking_text(raw):
    lines = [s.strip() for s in html.unescape(raw).replace('\\', '').replace('\u00a0', ' ').splitlines() if s.strip()]
    pattern = r'^(\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})),\s*(\d{1,2}:\d{2}),\s*(.+)$'
    dates = [(i, re.match(pattern, line)) for i, line in enumerate(lines)]
    dates = [(i, m) for i, m in dates if m]
    if len(dates) != 2 or not lines:
        raise ValueError('Нужны две строки: Д/М/ГГ, ЧЧ:ММ, место получения или возврата.')
    names = [name.strip() for name in lines[0].split('//') if name.strip()]
    first, _, last = names[0].partition(' ')
    data = {'driver_names': '\n'.join(names), 'driver_count': len(names), 'first_name': first,
            'last_name': last, 'customer_notes': raw, 'email': '', 'phone_1': '',
            'vehicle_group': '', 'existing_customer': '', 'vehicle_note': '', 'address': '',
            'cross_border_requested': False, 'extra_choices': [], 'child_seat_quantity': ''}
    for line in lines[1:dates[0][0]]:
        if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', line):
            data['email'] = line
        elif re.fullmatch(r'[+\d() -]+', line):
            data['phone_1'] = line
    for side, (_, match) in zip(('pickup', 'return'), dates):
        value, time, location = match.groups()
        try:
            parsed = datetime.strptime(value, '%d/%m/%Y' if len(value.split('/')[-1]) == 4 else '%d/%m/%y')
            time = datetime.strptime(time, '%H:%M').strftime('%H:%M')
        except ValueError:
            raise ValueError('Проверьте даты и время в исходном тексте.')
        data[side+'_date'] = parsed.strftime('%d-%m-%Y')
        data[side+'_time'] = time
        cities = {
            city.casefold(): city
            for city, _ in FirstInquiryForm.CITY_CHOICES
            if city and city != "OTHER"
        }
        cities.update({'krakow': 'Kraków', 'warsaw': 'Warszawa', 'wroclaw': 'Wrocław', 'gdansk': 'Gdańsk'})
        data[side+'_city'] = next((city for alias, city in cities.items() if re.search(r'\b'+re.escape(alias)+r'\b', location.casefold())), '')
        data[side+'_service'] = 'AIRPORT' if 'airport' in location.casefold() else 'ADDRESS'
        data[side+'_address'] = location
    tail = lines[dates[1][0]+1:]
    if tail and re.fullmatch(r'\d+\s+days?', tail[0], re.I):
        tail = tail[1:]
    if tail:
        data['vehicle_note'] = tail[0]
    price = next((i for i, line in enumerate(tail) if '=' in line and '//' in line), None)
    if price is not None:
        data['internal_notes'] = 'Цена и депозит из вставленного текста (проверить): ' + tail[price]
        data['address'] = ' '.join(tail[price+1:])
    else:
        data['internal_notes'] = 'Проверьте цену и адрес в исходном тексте.'
    data['cross_border_requested'] = bool(re.search(r'border crossing|travel abroad', raw, re.I))
    return data


@login_required
@require_POST
def paste_booking(request):
    raw = request.POST.get('text', '').strip()
    try:
        if not raw or len(raw) > 30000:
            raise ValueError('Вставьте текст заказа, не более 30 000 символов.')
        data = parse_booking_text(raw)
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    return JsonResponse({'fields': data})
