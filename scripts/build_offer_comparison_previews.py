"""Render the actual offer comparison template with public seeded facts only."""
import os
from pathlib import Path
from types import SimpleNamespace
from build_english_company_comparison import build

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.template.loader import render_to_string
from quotes.company_comparison import comparison_data

config, summaries = build()
options = [SimpleNamespace(supplier_id=index+1,
           supplier=SimpleNamespace(supplier_name=summary.name),
           supplier_name_snapshot=summary.name) for index, summary in enumerate(summaries)]
for summary in summaries:
    summary.supplier_id = None
out = Path(__file__).resolve().parents[1] / 'output/website-review'
for language, code in [('Hebrew','he'), ('English','en'), ('Polish','pl')]:
    data = comparison_data(options, summaries, config.content, language)
    html = render_to_string('quotes/company_comparison.html', {
        'company_comparison': data, 'is_ltr': language != 'Hebrew'})
    path = out / ('offer-comparison-'+code+'.html')
    path.write_text('<!doctype html><html lang="'+code+'" dir="'+('rtl' if code=='he' else 'ltr')+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Offer comparison preview</title></head><body style="font-family:Arial;max-width:700px;margin:20px auto;padding:12px">'+html+'</body></html>', encoding='utf-8')
    print(path)
