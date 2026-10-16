from types import SimpleNamespace
from django.test import SimpleTestCase
from .sections import arrange_sections


class SectionTests(SimpleTestCase):
    def option(self, pk, section):
        return SimpleNamespace(pk=pk, vehicle_group=SimpleNamespace(offer_section=section))

    def test_grouping_preserves_every_option_and_relative_order(self):
        options = [self.option(1, 'premium'), self.option(2, 'cars'),
                   self.option(3, 'crossovers'), self.option(4, 'premium')]
        result = arrange_sections(options, {'section_labels': {'cars': 'TEST-CARS',
            'premium': 'TEST-PREMIUM', 'crossovers': 'TEST-CROSS'}})
        self.assertEqual([o.pk for o in result], [2, 3, 1, 4])
        self.assertEqual([o.section_heading for o in result], ['TEST-CARS', 'TEST-CROSS', 'TEST-PREMIUM', ''])

    def test_one_section_has_no_redundant_heading(self):
        options = [self.option(1, 'premium'), self.option(2, 'premium')]
        self.assertEqual([o.section_heading for o in arrange_sections(options,
            {'section_labels': {'premium': 'TEST'}})], ['', ''])
