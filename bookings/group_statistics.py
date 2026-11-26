"""Read-only ranking of supplier vehicle groups by booked rental days."""
def top_rental_groups(records, limit=10):
    groups = {}
    missing = 0
    for record in records:
        if not record['group'] or not record['days'] or not record['month']:
            missing += 1
            continue
        key = (record['supplier_id'], record['group_key'])
        if key not in groups:
            groups[key] = dict(group=record['group'], supplier=record['supplier'], days=0,
                               winter=0, spring=0, summer=0, autumn=0, count=0)
        row = groups[key]
        season = ('winter' if record['month'] in (12, 1, 2) else 'spring'
                  if record['month'] in (3, 4, 5) else 'summer'
                  if record['month'] in (6, 7, 8) else 'autumn')
        row['days'] += record['days']
        row[season] += record['days']
        row['count'] += 1
    return sorted(groups.values(), key=lambda row: (-row['days'], row['supplier'], row['group']))[:limit], missing
