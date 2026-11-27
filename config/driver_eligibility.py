"""Driver eligibility uses supplier configuration, never supplier identities."""
from dataclasses import dataclass


def conditional_driver_details(data, count):
    """Only individually marked drivers require numeric facts at booking."""
    rows = []
    for index in range(1, count + 1):
        if not data.get(f'driver_{index}_young'):
            continue
        age, months = data.get(f'driver_{index}_age'), data.get(f'driver_{index}_license_months')
        validate_driver_profile(age, months)
        rows.append({'age': age, 'license_months': months})
    return validate_driver_details({'exception': bool(rows), 'drivers': rows}, count)


def validate_driver_profile(age, months):
    if type(age) is not int or not 16 <= age <= 100:
        raise ValueError('Enter age in full years, from 16 to 100.')
    if type(months) is not int or not 0 <= months <= age * 12:
        raise ValueError('Enter licence experience in full months.')


def validate_driver_details(value, driver_count=20):
    """Empty data preserves legacy records; explicit data must be complete."""
    if value in (None, {}):
        return {}
    if not isinstance(value, dict) or type(value.get('exception')) is not bool:
        raise ValueError('Invalid driver declaration.')
    rows = value.get('drivers', [])
    if not isinstance(rows, list) or len(rows) > driver_count:
        raise ValueError('Check the number of drivers.')
    if value['exception'] and not rows:
        raise ValueError('Enter age and licence experience for each affected driver.')
    if not value['exception'] and rows:
        raise ValueError('Check the driver declaration.')
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid driver details.')
        age, months = row.get('age'), row.get('license_months')
        validate_driver_profile(age, months)
        if age >= 24 and months >= 12:
            raise ValueError('Only drivers under 24 or with less than 12 months of licence experience belong here.')
        clean.append({'age': age, 'license_months': months})
    return {'exception': value['exception'], 'drivers': clean}


@dataclass(frozen=True)
class DriverAssessment:
    eligible: bool
    charged_drivers: int = 0
    reason: str = ''
    driver_number: int = 0


def assess_drivers(details, *, minimum_age, minimum_license_months, rules):
    """Pure check. Two surcharge conditions for one person count only once."""
    details = validate_driver_details(details)
    if not details:
        return DriverAssessment(True)
    if not rules or minimum_age is None or minimum_license_months is None:
        return DriverAssessment(False, reason='Driver requirements need confirmation.')
    if any(type(rules.get(key, 0)) is not int or rules.get(key, 0) < 0
           for key in ('surcharge_age_below', 'surcharge_license_months_below')):
        return DriverAssessment(False, reason='Driver requirements need confirmation.')
    charged = 0
    for index, row in enumerate(details['drivers'], 1):
        if row['age'] < minimum_age or row['license_months'] < minimum_license_months:
            return DriverAssessment(False, reason=f'Driver {index}: minimum age {minimum_age}; minimum licence experience {minimum_license_months} months.', driver_number=index)
        charged += int(row['age'] < rules.get('surcharge_age_below', 0)
                       or row['license_months'] < rules.get('surcharge_license_months_below', 0))
    return DriverAssessment(True, charged)


def assess_supplier_drivers(supplier, details, language=None):
    try:
        result = assess_drivers(details, minimum_age=supplier.minimum_driver_age,
            minimum_license_months=supplier.minimum_license_months,
            rules=supplier.customer_conditions.get('driver_rules'))
    except ValueError:
        return DriverAssessment(False, reason='Enter driver age and licence experience before calculating.')
    if result.driver_number:
        from django.utils.translation import get_language
        language = {'Hebrew': 'he', 'English': 'en', 'Polish': 'pl'}.get(language, language) or get_language()
        messages = supplier.customer_conditions.get('driver_rules', {}).get('messages', {})
        template = messages.get(language)
        if template:
            return DriverAssessment(False, reason=template.format(driver=result.driver_number,
                age=supplier.minimum_driver_age, months=supplier.minimum_license_months), driver_number=result.driver_number)
    return result
