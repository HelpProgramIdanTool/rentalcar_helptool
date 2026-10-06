import re

from .models import QuoteTemplate


def presentation_for(language):
    template = QuoteTemplate.objects.filter(language=language, is_active=True).first()
    return template.presentation if template else {}


def translate_text(text, presentation):
    translations = presentation.get("translations", {})
    if not text or not translations:
        return text
    # Match longer phrases first; never translate already translated output again.
    pattern = "|".join(re.escape(key) for key in sorted(translations, key=len, reverse=True))
    return re.sub(pattern, lambda match: translations[match.group()], text)


def offer_subject(quote):
    if quote.email_subject:
        return quote.email_subject
    label = presentation_for(quote.language).get("labels", {}).get("offer", "Car rental offer")
    return f"{label} {quote.quote_number}"


def prepare_calculation_display(options, language):
    """Add translated display fields without changing price/source snapshots."""
    presentation = presentation_for(language)
    for option in options:
        option["display_comparison_name"] = translate_text(option["comparison"].name, presentation)
        option["display_group_name"] = translate_text(option["group"].group_name, presentation)
        for key in ("body_type_label", "fuel_type_label", "transmission_label", "luggage_info"):
            option[f"display_{key}"] = translate_text(option.get(key, ""), presentation)
        for line in option.get("extra_lines", []):
            line["display_name"] = translate_text(line["name"], presentation)
