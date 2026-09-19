from math import ceil
from datetime import timezone


GRACE_PERIOD_SECONDS = 60 * 60
DAY_SECONDS = 24 * 60 * 60


def calculate_rental_days(pickup_datetime, return_datetime):
    """Count rental days with one free extra hour at the end."""
    if pickup_datetime.utcoffset() is not None and return_datetime.utcoffset() is not None:
        pickup_datetime = pickup_datetime.astimezone(timezone.utc)
        return_datetime = return_datetime.astimezone(timezone.utc)
    duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    chargeable_seconds = max(0, duration_seconds - GRACE_PERIOD_SECONDS)
    return max(1, ceil(chargeable_seconds / DAY_SECONDS))
