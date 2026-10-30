from datetime import date


def seasonal_included_items(start, end, rules):
    """Return configured wording for annually recurring periods that overlap rental dates."""
    if not start or not end or end < start:
        return []
    items = []
    for rule in rules:
        beginning = (int(rule['start_month']), int(rule['start_day']))
        ending = (int(rule['end_month']), int(rule['end_day']))
        for year in range(start.year - 1, end.year + 1):
            if year < 1:
                continue
            season_start = date(year, *beginning)
            season_end = date(year + (ending < beginning), *ending)
            if start <= season_end and end >= season_start:
                if rule['text'] and rule['text'] not in items:
                    items.append(rule['text'])
                break
    return items
