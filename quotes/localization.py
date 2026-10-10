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
    presentation = presentation_for(quote.language)
    if presentation.get("default_subject"):
        return presentation["default_subject"]
    label = presentation.get("labels", {}).get("offer", "Car rental offer")
    return f"{label} {quote.quote_number}"


def readable_terms(content):
    """Separate sentences for display without rewriting the stored conditions."""
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-ZА-Я\u0590-\u05ff])|\n+", content)
            if part.strip()]


def signature_display(content):
    """Style existing contact lines without changing their stored wording."""
    rows = []
    for index, line in enumerate(line.strip() for line in content.splitlines() if line.strip()):
        row = {"text": line, "kind": "name" if index == 1 else "text"}
        if re.fullmatch(r"https?://[^\s<>]+", line):
            row.update(kind="website", href=line, text=re.sub(r"^https?://", "", line).rstrip("/"))
        elif re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", line):
            row.update(kind="email", href="mailto:" + line)
        else:
            phone = re.search(r"\+\d[\d ()-]{6,}\d", line)
            if phone:
                row.update(kind="phone", text=phone.group(), label=line[:phone.start()].strip(),
                           suffix=line[phone.end():].strip(), href="tel:" + re.sub(r"[^+\d]", "", phone.group()))
        rows.append(row)
    return rows


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
