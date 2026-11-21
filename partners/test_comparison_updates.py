import importlib
from django.apps import apps
from django.test import TestCase
from django.template.loader import render_to_string
from .models import SupplierSummary, PortalConfiguration
from .forms import WorkspaceTripForm

class ComparisonUpdatesTests(TestCase):
    def test_update_merges_facts_without_erasing_custom_data(self):
        migration=importlib.import_module('partners.migrations.0008_foreign_handover_and_abroad_support')
        summary=SupplierSummary.objects.get(name='MM Cars')
        summary.facts={**summary.facts,'custom':'TEST CUSTOM'};summary.save()
        config=PortalConfiguration.objects.first()
        config.content={**config.content,'custom':'TEST COPY'};config.save()
        migration.seed(apps,None);migration.seed(apps,None)
        summary.refresh_from_db();config.refresh_from_db()
        self.assertEqual(summary.facts['gps_included'],migration.FACTS['mmcars']['gps_included'])
        self.assertEqual(summary.facts['foreign_handover'],migration.FACTS['mmcars']['foreign_handover'])
        self.assertEqual(summary.facts['custom'],'TEST CUSTOM')
        self.assertEqual(config.content['custom'],'TEST COPY')
        self.assertEqual(config.content['abroad_support'],migration.CONTENT['abroad_support'])

    def test_comparison_reads_new_facts_and_support_text_from_database(self):
        summary=SupplierSummary.objects.create(name='TEST COMPANY',facts={
            'foreign_handover':'TEST FOREIGN HANDOVER','gps_included':'TEST GPS INCLUDED'})
        config=PortalConfiguration.objects.first()
        config.content={**config.content,'foreign_handover_label':'TEST FOREIGN LABEL',
            'gps_included_label':'TEST GPS LABEL','abroad_support':{
                'title':'TEST ABROAD TITLE','body':'TEST COVERED SUPPORT','direct_booking_note':'TEST DIRECT NOTE'}}
        config.save();config.refresh_from_db()
        html=render_to_string('partners/comparison.html',{'summaries':[summary],'copy':config.content,'hide_gps':True})
        for value in ['TEST FOREIGN HANDOVER','TEST GPS INCLUDED','TEST ABROAD TITLE','TEST COVERED SUPPORT','TEST DIRECT NOTE','TEST FOREIGN LABEL','TEST GPS LABEL']:
            self.assertIn(value,html)
        self.assertNotIn('gps',WorkspaceTripForm().fields)
