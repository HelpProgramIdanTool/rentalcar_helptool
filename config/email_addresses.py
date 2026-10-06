import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def parse_email_addresses(value):
    """Validate every recipient; accept semicolons or commas and remove duplicates."""
    if '\r' in value or '\n' in value:
        raise ValidationError('Укажите email в одной строке через точку с запятой (;).')
    addresses, seen = [], set()
    for part in re.split(r'[;,]', value):
        address = part.strip()
        if not address:
            continue
        try:
            validate_email(address)
        except ValidationError:
            raise ValidationError('Неверный email: %(address)s.', params={'address': address})
        if address.casefold() not in seen:
            addresses.append(address)
            seen.add(address.casefold())
    if value.strip() and not addresses:
        raise ValidationError('Укажите хотя бы один email.')
    return addresses


def validate_email_addresses(value):
    parse_email_addresses(value)
