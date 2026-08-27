"""Generate a supplier extras report from the current Django database."""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.db.models import Prefetch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from suppliers.models import Supplier, SupplierExtra, SupplierExtraRate


OUTPUT_PATH = BASE_DIR / "output" / "pdf" / "supplier_extras_and_rates.pdf"


def register_fonts():
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("Report", regular))
        pdfmetrics.registerFont(TTFont("Report-Bold", bold))
        return "Report", "Report-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def money(value, currency):
    if value is None:
        return "-"
    return f"{value:.2f} {currency}"


def range_text(rate):
    parts = []
    if rate.days_from is not None or rate.days_to is not None:
        parts.append(f"days {rate.days_from or 1}-{rate.days_to or '+'}")
    if rate.minimum_amount_gross is not None:
        parts.append(f"min {money(rate.minimum_amount_gross, rate.currency)}")
    if rate.maximum_amount_gross is not None:
        parts.append(f"max {money(rate.maximum_amount_gross, rate.currency)}")
    if rate.location:
        parts.append(rate.location.location_name)
    return "; ".join(parts) or "-"


def formula_text(rate):
    if not rate.formula_config:
        return "-"
    return "; ".join(
        f"{key.replace('_', ' ')}: {value}"
        for key, value in rate.formula_config.items()
    )


def validity_text(rate):
    end = rate.valid_to.isoformat() if rate.valid_to else "open"
    return f"{rate.valid_from.isoformat()} to {end}"


def footer(canvas, document):
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(15 * mm, 9 * mm, "Supplier extras and gross customer prices")
    canvas.drawRightString(
        landscape(A3)[0] - 15 * mm,
        9 * mm,
        f"Page {document.page}",
    )
    canvas.restoreState()


def build_pdf(output_path=OUTPUT_PATH):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A3),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=13 * mm,
        bottomMargin=15 * mm,
        title="Supplier extras and rates",
        author="Rental Car Help Tool",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["Normal"],
        fontName=FONT,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )
    supplier_style = ParagraphStyle(
        "SupplierCustom",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0F766E"),
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=7.2,
        leading=9,
        alignment=TA_LEFT,
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=cell_style,
        fontName=FONT_BOLD,
    )

    rates = SupplierExtraRate.objects.select_related("location").order_by(
        "rate_code"
    )
    suppliers = Supplier.objects.prefetch_related(
        Prefetch(
            "extras",
            queryset=SupplierExtra.objects.filter(is_active=True)
            .order_by("category", "name")
            .prefetch_related(Prefetch("rates", queryset=rates)),
        )
    ).order_by("supplier_name")

    story = [
        Paragraph("Supplier extras and rates", title_style),
        Paragraph(
            "Data exported from the application database. All amounts are final customer prices including VAT.",
            subtitle_style,
        ),
        Spacer(1, 6 * mm),
    ]
    supplier_list = list(suppliers)
    for supplier_index, supplier in enumerate(supplier_list):
        extras = list(supplier.extras.all())
        rate_count = sum(len(list(item.rates.all())) for item in extras)
        story.append(
            Paragraph(
                f"{supplier.supplier_name} - {len(extras)} extras / {rate_count} rates",
                supplier_style,
            )
        )
        story.append(Spacer(1, 2 * mm))
        headers = [
            "Extra code",
            "Extra name",
            "Category",
            "Mandatory",
            "Rate code",
            "Calculation",
            "Gross price incl. VAT",
            "Limits / location",
            "Validity",
            "Formula / source price",
        ]
        rows = [[Paragraph(header, cell_bold) for header in headers]]
        for extra_obj in extras:
            extra_rates = list(extra_obj.rates.all())
            for rate_index, rate_obj in enumerate(extra_rates):
                source_price = rate_obj.note or "-"
                formula = formula_text(rate_obj)
                formula_and_source = source_price
                if formula != "-":
                    formula_and_source = f"{formula}; source: {source_price}"
                rows.append(
                    [
                        Paragraph(extra_obj.extra_code if rate_index == 0 else "", cell_style),
                        Paragraph(extra_obj.name if rate_index == 0 else "", cell_style),
                        Paragraph(extra_obj.category if rate_index == 0 else "", cell_style),
                        Paragraph("Yes" if extra_obj.is_mandatory and rate_index == 0 else "", cell_style),
                        Paragraph(rate_obj.rate_code, cell_style),
                        Paragraph(rate_obj.get_calculation_type_display(), cell_style),
                        Paragraph(money(rate_obj.amount_gross, rate_obj.currency), cell_style),
                        Paragraph(range_text(rate_obj), cell_style),
                        Paragraph(validity_text(rate_obj), cell_style),
                        Paragraph(formula_and_source, cell_style),
                    ]
                )
        table = Table(
            rows,
            repeatRows=1,
            colWidths=[24 * mm, 38 * mm, 24 * mm, 18 * mm, 21 * mm, 24 * mm, 28 * mm, 40 * mm, 33 * mm, 84 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)
        if supplier_index < len(supplier_list) - 1:
            story.append(PageBreak())
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output_path


if __name__ == "__main__":
    requested_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH
    print(build_pdf(requested_path))
