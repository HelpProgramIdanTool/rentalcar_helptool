from math import ceil


GRACE_PERIOD_SECONDS = 60 * 60
DAY_SECONDS = 24 * 60 * 60


def calculate_rental_days(pickup_datetime, return_datetime):
    """Count rental days with one free extra hour at the end."""
    duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    chargeable_seconds = max(0, duration_seconds - GRACE_PERIOD_SECONDS)
    return max(1, ceil(chargeable_seconds / DAY_SECONDS))
