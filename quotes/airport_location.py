"""Recognize explicit airport locations without treating airport hotels as terminals."""
import re


def is_airport_location(value):
    text = (value or '').strip().casefold()
    if re.search(r'\b(?:hotel|motel|hostel|apartments?)\b|отел|гостиниц|מלון', text):
        return False
    return bool(re.search(r'\bairport\b|\blotnisko\b|\bport\s+lotniczy\b|аэропорт|שדה\s*(?:ה)?תעופה|נמל\s*(?:ה)?תעופה', text))


def airport_service_conflicts(data):
    return [side for side in ('pickup', 'return')
            if data.get(side+'_service') == 'ADDRESS'
            and is_airport_location(data.get(side+'_address'))]
