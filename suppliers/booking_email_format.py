"""Validate the supplier-editable format; only scalar placeholders are allowed."""
from string import Template

FIELDS = frozenset({'customer','driver_names','address','phone','email','pickup_date','pickup_location',
    'flight_number','return_date','return_location','vehicle_class','days','services','deposit','price_calculation'})
OPTIONS = {'included_services':list, 'service_names':dict, 'skip_service_codes':list,
           'airport_service_label':str, 'city_names':dict}


def validate_booking_email_format(template, options):
    parsed = Template(template)
    if not parsed.is_valid():
        raise ValueError('Invalid $placeholder syntax in the supplier template.')
    unknown = set(parsed.get_identifiers()) - FIELDS
    if unknown:
        raise ValueError('Unknown supplier template fields: '+', '.join(sorted(unknown)))
    if not isinstance(options,dict) or set(options)-set(OPTIONS):
        raise ValueError('Unknown supplier template options.')
    for key, value in options.items():
        if not isinstance(value,OPTIONS[key]):
            raise ValueError('Invalid supplier template option: '+key)
        if isinstance(value,list) and any(not isinstance(item,str) for item in value):
            raise ValueError('Supplier service lists must contain text.')
        if isinstance(value,dict) and any(not isinstance(k,str) or not isinstance(v,str) for k,v in value.items()):
            raise ValueError('Supplier service and city mappings must contain text.')
