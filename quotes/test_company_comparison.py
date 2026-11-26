from importlib import import_module
from types import SimpleNamespace
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from .company_comparison import comparison_data, offer_company_comparison


def option(pk, name):
    return SimpleNamespace(supplier_id=pk, supplier=SimpleNamespace(supplier_name=name), supplier_name_snapshot=name)


class ComparisonTests(SimpleTestCase):
    def test_comparison_cards_keep_each_company_fact_and_need_no_scroll_or_media_query(self):
        for language in ['Hebrew', 'English', 'Polish']:
            second=SimpleNamespace(supplier_id=2,name='TEST-TWO',facts={
                'age':'SECOND-HE','translations':{'English':{'age':'SECOND-EN'},'Polish':{'age':'SECOND-PL'}}})
            data=comparison_data([option(1,'TEST-ONE'),option(2,'TEST-TWO')],[self.summary,second],self.content,language)
            self.assertEqual(data['companies'][0]['rows'][0]['label'],'Age')
            self.assertEqual(data['companies'][1]['rows'][0]['value'],data['rows'][0]['values'][1])
            html=render_to_string('quotes/company_comparison.html',{'company_comparison':data,'is_ltr':language!='Hebrew'})
            self.assertEqual(html.count('class="comparison-company"'),2)
            self.assertIn('table-layout:fixed',html)
            self.assertIn('width:100%;max-width:280px',html)
            self.assertNotIn('overflow-x',html)
            self.assertNotIn('@media',html)
            self.assertIn(data['companies'][0]['rows'][0]['value'],html)
            self.assertIn(data['companies'][1]['rows'][0]['value'],html)

    def setUp(self):
        self.content = {'offer_comparison': {language: {
            'title': 'TEST-TITLE-'+language, 'keys': ['age'], 'columns': ['Company', 'Age'],
            'unknown': 'TEST-UNKNOWN', 'url': 'https://example.com/'+language,
            'link_label': 'TEST-LINK', 'common': 'TEST-COMMON', 'note': 'TEST-NOTE'
        } for language in ['Hebrew', 'English', 'Polish']}}
        self.summary = SimpleNamespace(supplier_id=1, name='TEST-ONE', facts={
            'age': 'TEST-HE', 'translations': {'English': {'age': 'TEST-EN'}, 'Polish': {'age': 'TEST-PL'}}})

    def test_only_selected_suppliers_once_and_correct_language(self):
        excluded = SimpleNamespace(supplier_id=2, name='EXCLUDED', facts={'age': 'NOT-SHOWN'})
        for language, value in [('Hebrew', 'TEST-HE'), ('English', 'TEST-EN'), ('Polish', 'TEST-PL')]:
            with self.subTest(language=language):
                data = comparison_data([option(1,'TEST-ONE'), option(1,'TEST-ONE')], [self.summary, excluded], self.content, language)
                self.assertEqual(len(data['companies']),1)
                self.assertEqual(data['rows'][0]['values'], [value])
                html = render_to_string('quotes/company_comparison.html', {'company_comparison': data, 'is_ltr': language != 'Hebrew'})
                self.assertIn(value, html)
                self.assertIn(data['url'], html)
                self.assertNotIn('NOT-SHOWN', html)

    def test_unlinked_summary_matches_supplier_name_and_unknown_never_leaks_hebrew(self):
        self.summary.supplier_id = None
        self.assertEqual(comparison_data([option(1,'TEST-ONE')],[self.summary],self.content,'English')['rows'][0]['values'],['TEST-EN'])
        self.summary.facts['translations'] = {}
        self.assertEqual(comparison_data([option(1,'TEST-ONE')],[self.summary],self.content,'English')['rows'][0]['values'],['TEST-UNKNOWN'])

    def test_empty_or_unconfigured_comparison_is_omitted(self):
        self.assertIsNone(comparison_data([], [self.summary], self.content, 'English'))
        self.assertIsNone(comparison_data([option(1,'TEST')], [], {}, 'English'))

    def test_full_offer_places_comparison_after_options_heading_and_plain_text_has_link(self):
        for language in ['Hebrew', 'English', 'Polish']:
            data = comparison_data([option(1, 'TEST-ONE')], [self.summary], self.content, language)
            context = {'is_email': True, 'is_english': language == 'English',
                       'is_polish': language == 'Polish', 'is_localized': language == 'Polish',
                       'is_ltr': language != 'Hebrew', 'company_comparison': data,
                       'offer_labels': {'options': 'TEST-OPTIONS'}}
            html = render_to_string('quotes/quote_preview.html', context)
            self.assertLess(html.index('class="options-title"'), html.index('offer-company-comparison'))
            self.assertIn(data['url'], html)
            text = render_to_string('quotes/quote_email.txt', context)
            self.assertIn(data['url'], text)
            self.assertIn('TEST-COMMON', text)


class ComparisonDatabaseTests(TestCase):
    def test_configuration_is_read_from_database(self):
        from partners.models import PortalConfiguration, SupplierSummary
        config = PortalConfiguration.objects.first()
        data = config.content['offer_comparison']['English']
        data['url'] = 'https://example.com/TEST-DB-LINK'
        config.save()
        summary = SupplierSummary.objects.first()
        summary.facts['translations']['English']['age'] = 'TEST-DB-VALUE'
        summary.save()
        result = offer_company_comparison([option(912, summary.name)], 'English')
        self.assertEqual(result['url'], data['url'])
        self.assertEqual(result['rows'][0]['values'], ['TEST-DB-VALUE'])

    def test_seed_preserves_custom_wording_and_existing_facts(self):
        from django.apps import apps
        from partners.models import PortalConfiguration, SupplierSummary
        config = PortalConfiguration.objects.first()
        config.content['offer_comparison']['English']['title'] = 'TEST-CUSTOM'
        config.save()
        summary = SupplierSummary.objects.first()
        summary.facts['translations']['English']['age'] = 'TEST-CUSTOM-AGE'
        summary.facts['custom'] = 'KEEP'
        summary.save()
        import_module('partners.migrations.0009_offer_company_comparison').seed(apps, None)
        config.refresh_from_db(); summary.refresh_from_db()
        self.assertEqual(config.content['offer_comparison']['English']['title'], 'TEST-CUSTOM')
        self.assertEqual(summary.facts['translations']['English']['age'], 'TEST-CUSTOM-AGE')
        self.assertEqual(summary.facts['custom'], 'KEEP')
