from datetime import date, datetime
from django import template

register = template.Library()


@register.filter
def portal_date(value):
    if isinstance(value, (date, datetime)):
        return value.strftime('%d.%m.%Y')
    try:
        return date.fromisoformat(str(value)).strftime('%d.%m.%Y')
    except (ValueError, TypeError):
        return value
