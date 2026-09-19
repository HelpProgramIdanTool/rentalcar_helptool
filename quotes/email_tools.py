from pathlib import Path
from django.conf import settings
from .email_content import REQUIRED_BLOCKS
from .models import QuoteDocumentBlock, QuoteTemplate
from suppliers.models import Supplier

GUIDES = {
    "01": ("Kaizen", "ריכוז חוקים אודות כיסאות בטיחות ובוסטרים.pdf", "Kaizen-child-seats.pdf"),
    "02": ("One Rent", "Rules for transporting children by car in Poland.pdf", "One-Rent-child-seats.pdf"),
}


def supplier_introduction():
    return ", ".join(Supplier.objects.filter(show_in_introduction=True).values_list("supplier_name", flat=True))


def load_email_template(quote, *, replace=False):
    template = QuoteTemplate.objects.filter(language=quote.language, is_active=True).first()
    if not template:
        template = QuoteTemplate.objects.filter(language="Hebrew", is_active=True).first()
    if not template:
        return
    if replace:
        quote.document_blocks.all().delete()
    names = supplier_introduction()
    for block in template.blocks.filter(is_active=True):
        QuoteDocumentBlock.objects.get_or_create(quote=quote, block_key=block.block_key, defaults={
            "source_block": block, "title": block.title,
            "content": block.content.replace("{suppliers}", names or "חברות ההשכרה השותפות שלנו"),
            "display_order": block.display_order,
            "is_enabled": bool(block.content) or block.block_key in REQUIRED_BLOCKS,
        })


def ensure_required_blocks(quote):
    template = QuoteTemplate.objects.filter(language="Hebrew", is_active=True).first()
    if not template:
        return
    for source in template.blocks.filter(block_key__in=REQUIRED_BLOCKS | {"SIGNATURE"}):
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
    codes = set(quote.options.filter(is_included=True).values_list("supplier__supplier_code", flat=True))
    return [dict(code=code, supplier=label, filename=filename,
                 path=Path(settings.BASE_DIR) / "assets" / "customer-guides" / source)
            for code, (label, source, filename) in GUIDES.items() if code in codes]


def child_seat_text(quote, guides):
    try:
        needed = int(quote.extra_requests.get("CHILD_SEAT", 0)) > 0
    except (ValueError, TypeError):
        needed = False
    if not needed:
        return ""
    text = "אם ביקשתם כיסא בטיחות או בוסטר, חשוב להתייחס לבחירה באחריות ולמסור את הגיל, הגובה והמשקל של כל ילד."
    if guides:
        text += " אנא קראו בעיון את ההסברים בקבצים המצורפים של חברות ההשכרה הרלוונטיות."
    if any(guide["code"] == "02" for guide in guides):
        text += " בהצעה של One Rent יש לציין גם את מספר סוג הכיסא המבוקש (1–5), בהתאם לקובץ."
    return text
