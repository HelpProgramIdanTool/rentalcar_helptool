"""Check downloaded public pages: uv run python wordpress/tests/check_backup_pages.py."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == 'a':
            self.links.append(dict(attrs).get('href'))


class PublicBackupPagesTests(unittest.TestCase):
    def test_public_pages_have_links_and_do_not_embed_login_or_tracking(self):
        for name in ('about', 'privacy', 'terms'):
            with self.subTest(page=name):
                html = Path(f'tmp/backup-{name}.html').read_text(encoding='utf-8')
                headers = Path(f'tmp/backup-{name}.headers').read_text()
                self.assertIn('200 OK', headers)
                page = Page(html)
                self.assertIn('h1', page.tags)
                self.assertNotIn('script', page.tags)
                self.assertNotIn('form', page.tags)
                self.assertNotIn('iframe', page.tags)
                for slug in ('rentalcar-backups', 'rentalcar-backups-privacy', 'rentalcar-backups-terms'):
                    self.assertIn(f'/{slug}/', page.links)
                self.assertIn('mailto:idan.poland@gmail.com', page.links)

    def test_privacy_explains_access_use_retention_and_revocation(self):
        html = Path('tmp/backup-privacy.html').read_text(encoding='utf-8')
        for text in ('drive.file', 'Limited Use', 'Retention and deletion',
                     'https://myaccount.google.com/connections', 'being configured'):
            self.assertIn(text, html)

    def test_pages_do_not_claim_backups_are_operational(self):
        html = Path('tmp/backup-about.html').read_text(encoding='utf-8')
        self.assertIn('have not yet been verified', html)


if __name__ == '__main__':
    unittest.main()
