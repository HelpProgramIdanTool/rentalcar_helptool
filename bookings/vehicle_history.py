"""Read a vehicle class from structured bookings or their original import."""


def booking_vehicle_label(booking):
    if booking.vehicle_group_id:
        group = booking.vehicle_group
        return group.group_name, group.group_code
    raw = (booking.source_quote_snapshot or {}).get('historical_import', {}).get('raw', {})
    return str(raw.get('D') or '').strip(), ''


def customer_vehicle_preferences(bookings):
    rows = {}
    for booking in bookings:
        name, code = booking_vehicle_label(booking)
        key = (booking.supplier_id, name, code)
        if key not in rows:
            rows[key] = {'supplier__supplier_name': str(booking.supplier),
                'vehicle_group__group_name': name, 'vehicle_group__group_code': code, 'count': 0}
        rows[key]['count'] += 1
        booking.history_group_name = name
        booking.history_group_code = code
    return sorted(rows.values(), key=lambda row: (-row['count'], row['supplier__supplier_name'], row['vehicle_group__group_name']))
