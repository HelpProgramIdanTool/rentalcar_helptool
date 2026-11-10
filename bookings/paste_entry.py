"""Parse a compact supplier request without creating or sending a booking."""
import html
import re
from datetime import datetime
from decimal import Decimal
from html.parser import HTMLParser

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from quotes.forms import FirstInquiryForm


class _VisibleMailText(HTMLParser):
    """Use visible link text, never a mailto target that may name someone else."""
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.skip=0

    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):
            self.skip+=1
        if tag in ('br','p','div','li','tr'):
            self.parts.append('\n')

    def handle_endtag(self,tag):
        if tag in ('script','style'):
            self.skip=max(0,self.skip-1)
        if tag in ('p','div','li','tr'):
            self.parts.append('\n')

    def handle_data(self,value):
        if not self.skip:
            self.parts.append(value)


LABEL = re.compile(r'^(?:customer\s+(?:name|phone(?:\s+number)?|email|address)|'
    r'pick[ -]?up(?:\s+details)?|drop[ -]?off(?:\s+details)?|'
    r'duration|category|extras|final\s+price)\s*:\s*', re.I)


def clean_mail_lines(raw):
    text=html.unescape(raw).replace('\u00a0',' ')
    if re.search(r'</?(?:a|br|p|div|strong|b|span|li|tr|td)\b',text,re.I):
        parser=_VisibleMailText()
        parser.feed(text)
        text=''.join(parser.parts)
    text=re.sub(r'\[([^\]]+)\]\((?:mailto:|tel:|https?://)[^)]*\)',r'\1',text)
    text=text.replace('**','')
    lines=[]
    for line in text.splitlines():
        line=line.strip().rstrip('\\').strip()
        line=re.sub(r'^>\s*','',line)
        line=LABEL.sub('',line).strip()
        if line:
            lines.append(line)
    return lines


def parse_booking_text(raw):
    lines = clean_mail_lines(raw)
    pattern = r'^(\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})),\s*(\d{1,2}:\d{2}),\s*(.+)$'
    dates = [(i, re.match(pattern, line)) for i, line in enumerate(lines)]
    dates = [(i, m) for i, m in dates if m]
    if len(dates) != 2 or not lines:
        raise ValueError('Нужны две строки: Д/М/ГГ, ЧЧ:ММ, место получения или возврата.')
    names = [name.strip() for name in re.split(r'//|\|',lines[0]) if name.strip()]
    if not names:
        raise ValueError('Укажите имя клиента.')
    first, _, last = names[0].partition(' ')
    data = {'driver_names': '\n'.join(names), 'driver_count': len(names), 'first_name': first,
            'last_name': last, 'customer_notes': raw, 'email': '', 'phone_1': '', 'phone_2': '', 'phone_3': '',
            'vehicle_group': '', 'existing_customer': '', 'vehicle_note': '', 'address': '',
            'customer_name': names[0], 'flight_number': '',
            'cross_border_requested': False, 'extra_choices': [], 'child_seat_quantity': ''}
    phones = []
    for line in lines[1:dates[0][0]]:
        if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', line):
            data['email'] = line
        else:
            parts = [part.strip() for part in re.split(r'//|\||;', line) if part.strip()]
            if parts and all(re.fullmatch(r'[+\d() .-]+', part) and 7 <= len(re.sub(r'\D', '', part)) <= 15 for part in parts):
                for part in parts:
                    if part not in phones:
                        phones.append(part)
    if len(phones) > 3:
        raise ValueError('В тексте больше трёх телефонов. Выберите до трёх контактных номеров.')
    data.update({f'phone_{index}': value for index, value in enumerate(phones, 1)})
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
        if side=='pickup' and data[side+'_service']=='AIRPORT':
            flight=re.search(r'\b([A-Z][A-Z0-9]|[0-9][A-Z])\s*(\d{2,4})\b',location)
            if flight:
                data['flight_number']=flight.group(1)+' '+flight.group(2)
    tail = lines[dates[1][0]+1:]
    if tail and re.fullmatch(r'\d+\s+days?', tail[0], re.I):
        tail = tail[1:]
    if tail:
        data['vehicle_note'] = tail[0]
    price = next((i for i, line in enumerate(tail) if ('//' in line or '||' in line)
                  and ('=' in line or re.match(r'^\d',line))), None)
    if price is not None:
        data['internal_notes'] = 'Цена и депозит из вставленного текста (проверить): ' + tail[price]
        data['address'] = ' '.join(tail[price+1:])
        parts=re.split(r'//|\|\|',tail[price],maxsplit=1)
        for key,value in zip(('pasted_total_gross','pasted_deposit'),parts):
            match=re.fullmatch(r'\s*(\d+(?:[.,]\d{1,2})?)\s*(?:PLN|EUR|CZK)?\s*',value.rsplit('=',1)[-1],re.I)
            if match:
                data[key]=format(Decimal(match.group(1).replace(',','.')),'.2f')
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
