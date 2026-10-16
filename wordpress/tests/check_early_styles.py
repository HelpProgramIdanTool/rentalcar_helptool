"""Compare downloaded before/after HTML: uv run python wordpress/tests/check_early_styles.py."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

if not settings.configured:
    settings.configure(SECRET_KEY="test-only", DATABASES={})


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in {"img", "iframe", "input", "form", "script", "link"}:
            self.elements.append((tag, sorted(attrs, key=lambda item: item[0])))


class EarlyStylesResponseTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.before = Path("tmp/early-styles-before.html").read_text(encoding="utf-8")
        cls.after = Path("tmp/early-styles-after.html").read_text(encoding="utf-8")
        cls.pattern = r'<style\b[^>]*\bid=["\']et-builder-module-design-[^"\']+-deferred-[^"\']+-cached-inline-styles["\'][^>]*>.*?</style>'

    def test_original_style_is_preserved_once_and_moved_into_head(self):
        before = list(re.finditer(self.pattern, self.before, re.S | re.I))
        after = list(re.finditer(self.pattern, self.after, re.S | re.I))
        self.assertEqual(len(before), 1)
        self.assertEqual(len(after), 1)
        self.assertEqual(before[0].group(), after[0].group())
        self.assertGreater(before[0].start(), self.before.lower().index("</head>"))
        self.assertLess(after[0].end(), self.after.lower().index("</head>") + 1)

    def test_other_style_elements_keep_contents_and_order(self):
        def remaining(html):
            html = re.sub(self.pattern, "", html, flags=re.S | re.I)
            return re.findall(r"<style\b[^>]*>.*?</style>", html, re.S | re.I)
        self.assertEqual(remaining(self.before), remaining(self.after))

    def test_media_forms_and_scripts_are_unchanged(self):
        self.assertEqual(Elements(self.before).elements, Elements(self.after).elements)


if __name__ == "__main__":
    unittest.main()
