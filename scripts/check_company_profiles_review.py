"""Check the three connected preview files without contacting production."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1] / 'output/website-review'

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.headings = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'a':
            self.links.append(a.get('href', ''))
        if tag == 'h1':
            self.headings += 1
        if tag == 'html':
            assert a['lang'] == 'he' and a['dir'] == 'rtl'
        if tag == 'img':
            assert a.get('alt') and a['src'].startswith('data:')

for name in ['rental-companies-review.html', 'car-free-review.html', 'mm-cars-review.html']:
    page = Page()
    page.feed((ROOT / name).read_text(encoding='utf-8'))
    assert page.headings == 1
    assert len(page.ids) == len(set(page.ids))
    for link in page.links:
        if link.startswith('#'):
            assert link[1:] in page.ids
        elif not link.startswith(('https:', 'mailto:')):
            target = ROOT / link.split('#')[0]
            assert target.is_file(), link
    assert urlopen('http://127.0.0.1:8786/' + name, timeout=10).status == 200
    print(name + ': headings, Hebrew direction, images, links and HTTP passed')
