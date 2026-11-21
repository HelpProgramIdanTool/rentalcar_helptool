"""Prepare the approved Kaizen draft for its existing WordPress address."""
import build_kaizen_profile_review  # Registers and builds the approved profile.
import prepare_company_pages_publication as publication
import json

publication.PAGES.append((
    'kaizen-rent-review.html', 'kaizen-rent',
    'Kaizen Rent — מידע מעשי להשכרת רכב בפולין',
    'Kaizen Rent בפולין: קבלה והחזרה בטרמינל, מדיניות דלק, קבוצות רכב, מגבלות מסירה בחו״ל והיתרונות בהזמנה עם ליווי אישי של עידן.',
))
publication.prepare()
# The existing Kaizen Divi page does not output a theme H1, unlike new pages.
path = publication.OUT / 'wordpress-publication.json'
pages = json.loads(path.read_text(encoding='utf-8'))
page = next(p for p in pages if p['slug'] == 'kaizen-rent')
page['content'] = page['content'].replace(
    '<p class="lead">', '<h1>'+page['title']+'</h1><p class="lead">', 1)
path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
