"""Prepare the One Rent refresh, preserving its original YouTube video."""
import json
import build_one_rent_profile_review as draft
import prepare_company_pages_publication as publication

publication.PAGES.append((
    'one-rent-review.html', 'one-rent',
    'One Rent — רכבים חדשים, שירות אישי ומבחר רחב',
    'One Rent בפולין: רכבים עד גיל שנתיים, מבחר קבוצות, שירות קשוב וליווי של עידן לפתרון בעיות. מידע על מסירה, ביטוח ותנאי ההשכרה.',
))
publication.prepare()
path = publication.OUT / 'wordpress-publication.json'
pages = json.loads(path.read_text(encoding='utf-8'))
page = next(p for p in pages if p['slug'] == 'one-rent')
# Existing Divi pages do not output a theme title.
page['content'] = page['content'].replace(
    '<p class="lead">', '<h1>'+page['title']+'</h1><p class="lead">', 1)
page['content'] = page['content'].replace(
    '<section class="personal-statement">', draft.video+'<section class="personal-statement">', 1)
assert page['content'].count('https://www.youtube.com/embed/91g1dlq2r1A') == 1
path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
