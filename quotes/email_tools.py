from pathlib import Path
from django.conf import settings
from .email_content import REQUIRED_BLOCKS
from .models import QuoteDocumentBlock, QuoteTemplate
from suppliers.models import Supplier
from .localization import presentation_for

def supplier_introduction():
    return ", ".join(Supplier.objects.filter(show_in_introduction=True).values_list("supplier_name", flat=True))


def load_email_template(quote, *, replace=False):
    template = QuoteTemplate.objects.filter(language=quote.language, is_active=True).first()
    if not template:
        return
    if replace:
        quote.document_blocks.all().delete()
    names = supplier_introduction()
    fallback = template.presentation.get("partner_fallback") or (
        "our partner rental companies" if quote.language == "English" else "חברות ההשכרה השותפות שלנו"
    )
    for block in template.blocks.filter(is_active=True):
        content = block.content.replace("{suppliers}", names or fallback)
        saved, created = QuoteDocumentBlock.objects.get_or_create(quote=quote, block_key=block.block_key, defaults={
            "source_block": block, "title": block.title,
            "content": content,
            "display_order": block.display_order,
            "is_enabled": bool(block.content) or block.block_key in REQUIRED_BLOCKS,
        })
        if (not created and saved.source_block_id
                and saved.source_block.template.language != quote.language):
            old = saved.source_block
            old_fallback = old.template.presentation.get("partner_fallback") or (
                "our partner rental companies" if old.template.language == "English" else "חברות ההשכרה השותפות שלנו"
            )
            expected = old.content.replace("{suppliers}", names or old_fallback)
            if (saved.content.replace("\r\n", "\n").strip() == expected.replace("\r\n", "\n").strip()
                    and saved.title == old.title):
                saved.source_block = block
                saved.title = block.title
                saved.content = content
                saved.save(update_fields=["source_block", "title", "content"])


def ensure_required_blocks(quote):
    template = QuoteTemplate.objects.filter(language=quote.language, is_active=True).first()
    if not template:
        return
    for source in template.blocks.filter(block_key__in=REQUIRED_BLOCKS | {"SIGNATURE", "AI_NOTE"}):
        block, created = quote.document_blocks.get_or_create(block_key=source.block_key, defaults={
            "source_block": source, "title": source.title, "content": source.content,
            "display_order": source.display_order, "is_enabled": True,
        })
        if (not created and block.source_block_id and block.source_block_id != source.pk
                and block.content.replace("\r\n", "\n").strip() == block.source_block.content.replace("\r\n", "\n").strip()):
            block.source_block = source
            block.content = source.content
            block.title = source.title
            block.is_enabled = True
            block.save()


def seat_guides(quote):
    try:
        seats = int(quote.extra_requests.get("CHILD_SEAT", 0))
    except (ValueError, TypeError):
        seats = 0
    if seats < 1:
        return []
    from partners.models import PortalConfiguration
    config = PortalConfiguration.objects.first()
    guides = (config.content or {}).get('child_seat_guides', {}) if config else {}
    by_name = {''.join(key.casefold().split()): value for key, value in guides.items()}
    result, seen = [], set()
    for code, name in quote.options.filter(is_included=True).order_by('supplier__supplier_code').values_list('supplier__supplier_code', 'supplier__supplier_name'):
        if code in seen:
            continue
        seen.add(code)
        guide = guides.get(code) or by_name.get(''.join(name.casefold().split()))
        if not guide:
            continue
        label, source, filename = guide
        private = source.startswith('private:')
        source = source.removeprefix('private:')
        if Path(source).name != source or Path(filename).name != filename:
            raise ValueError('Child-seat guide configuration must contain filenames only.')
        root = Path(settings.MEDIA_ROOT) if private else Path(settings.BASE_DIR) / 'assets'
        result.append(dict(code=code, supplier=label, filename=filename, private=private,
            path=root / 'customer-guides' / source))
    return result


def child_seat_text(quote, guides):
    try:
        needed = int(quote.extra_requests.get("CHILD_SEAT", 0)) > 0
    except (ValueError, TypeError):
        needed = False
    if not needed:
        return ""
    presentation = presentation_for(quote.language)
    if presentation.get("child_seat"):
        return " ".join(part for part in (
            presentation["child_seat"],
            presentation.get("child_seat_guides", "") if guides else "",
            presentation.get("child_seat_one_rent", "") if any(guide["code"] == "02" for guide in guides) else "",
        ) if part)
    if quote.language == "English":
        text = "If you requested a child seat or booster, please provide the age, height and weight of each child."
        if guides:
            text += " Please read the attached instructions from the relevant rental companies."
        if any(guide["code"] == "02" for guide in guides):
            text += " For One Rent, also provide the requested seat type number (1–5) shown in the attachment."
        return text
    text = "אם ביקשתם כיסא בטיחות או בוסטר, חשוב להתייחס לבחירה באחריות ולמסור את הגיל, הגובה והמשקל של כל ילד."
    if guides:
        text += " אנא קראו בעיון את ההסברים בקבצים המצורפים של חברות ההשכרה הרלוונטיות."
    if any(guide["code"] == "02" for guide in guides):
        text += " בהצעה של One Rent יש לציין גם את מספר סוג הכיסא המבוקש (1–5), בהתאם לקובץ."
    return text
