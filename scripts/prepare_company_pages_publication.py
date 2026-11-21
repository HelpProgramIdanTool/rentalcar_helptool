"""Prepare approved content for WordPress; this script does not publish it."""
import json
import re
from pathlib import Path
from build_company_profiles_review import main, LINKS
from build_rental_companies_review import STYLE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/website-review'
BASE = 'https://poland-rent-car.com'
PAGES = [
    ('rental-companies-review.html', 'rental-companies',
     'השוואת חברות השכרת רכב בפולין — הסטנדרט של עידן',
     'השוואה מעשית בין Kaizen, Car Free, One Rent ו-MM Cars: ביטוח, פיקדון, דלק, מסירה וסיוע בחו״ל, עם שירות אישי של עידן.'),
    ('car-free-review.html', 'car-free',
     'Car Free — השכרת רכב בפולין ובפראג עם עידן',
     'מידע מעשי על Car Free: צי חדיש, מסירה בטרמינל, מדיניות דלק, השכרה בפראג ותנאי נסיעה לחו״ל במסגרת ההצעה של עידן.'),
    ('mm-cars-review.html', 'mm-cars',
     'MM Cars — השכרת רכב בפולין עם עידן',
     'מידע מעשי על MM Cars: רכבים עד גיל שנתיים, GPS בכל רכב, דלק מלא למלא, הוראות החזרה וסיוע בחו״ל במסגרת ההצעה של עידן.'),
]

def prepare():
    main()
    replacements = {filename: f'{BASE}/{slug}/' for filename, slug, _, _ in PAGES}
    payload = []
    for filename, slug, title, description in PAGES:
        source = (OUT / filename).read_text(encoding='utf-8')
        content = re.search(r'<main\b[^>]*>(.*?)</main>', source, re.S).group(1)
        for old, new in replacements.items():
            content = content.replace(old, new)
        # Review notes are outside main. WordPress/theme supplies the document,
        # navigation, language attributes, canonical and SEO graph.
        assert '127.0.0.1' not in content
        assert '-review.html' not in content
        assert 'review-bar' not in content
        def scope(match):
            selector = match.group(1).strip()
            if selector.startswith('@'):
                return selector + '{'
            return ','.join('.prc-company-page ' + s.strip() for s in selector.split(',')) + '{'
        css = re.sub(r'([^{}]+)\{', scope, STYLE)
        css += '''.prc-company-page{--navy:#163960;--blue:#145f9e;--ink:#25374a;--muted:#627387;--line:#dce4ed;--gold:#ffdf70;color:var(--ink);direction:rtl;font:16px/1.75 Arial,sans-serif;max-width:1120px;margin:auto}.prc-company-page img{max-width:100%}.prc-company-page .explain{margin:20px 0}.prc-company-page h1{font-size:clamp(29px,4vw,45px)}body:has(.prc-company-page) #sidebar{display:none}body:has(.prc-company-page) #left-area{width:100%;padding:0}body:has(.prc-company-page) #main-content .container:before{display:none}body:has(.prc-company-page) .entry-title{display:none}'''
        content = re.sub(r'<h1>[\s\S]*?</h1>', '', content)
        css = css.replace('body:has(.prc-company-page) .entry-title{display:none}', 'body:has(.prc-company-page) .entry-title{display:block;font-size:clamp(28px,4vw,42px);color:#163960;line-height:1.3}')
        content = '<style>' + css + '</style><div class="prc-company-page" lang="he" dir="rtl">' + content + '</div>'
        payload.append(dict(slug=slug, title=title, seo_title=title,
                            seo_description=description, language='he',
                            canonical=f'{BASE}/{slug}/', content=content,
                            status='publish'))
    (OUT / 'wordpress-publication.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Prepared three publication payloads; WordPress unchanged.')

if __name__ == '__main__':
    prepare()
