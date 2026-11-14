from types import SimpleNamespace
from django.test import SimpleTestCase, TestCase
from suppliers.models import Supplier, RentalCountry, OfferCity, SupplierLocalBranch
from .country_rules import route_flags, route_context, location_country, localize_country_text


class RouteFlagsTests(SimpleTestCase):
    def test_czech_local_and_both_cross_border_directions(self):
        self.assertFalse(route_flags('CZ', 'CZ', 'CZ')['cross_border'])
        self.assertTrue(route_flags('CZ', 'CZ', 'PL')['cross_border'])
        self.assertTrue(route_flags('CZ', 'PL', 'CZ')['cross_border'])
        self.assertTrue(route_flags('CZ', 'CZ', 'CZ', declared=True)['cross_border'])

    def test_only_foreign_pickup_needs_prepayment_and_local_branch_can_waive(self):
        self.assertFalse(route_flags('PL', 'PL', 'SK')['prepayment'])
        self.assertTrue(route_flags('PL', 'SK', 'PL')['prepayment'])
        self.assertFalse(route_flags('CZ', 'CZ', 'CZ', pickup_waiver=True)['prepayment'])


class CountryConfigurationTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(supplier_code='COUNTRY-TEST', supplier_name='TEST BRANCH')
        self.city = OfferCity.objects.create(name='TEST Prague', label='TEST', country='Czechia')
        self.country = RentalCountry.objects.get(code='CZ')
        SupplierLocalBranch.objects.create(supplier=self.supplier, city=self.city, country=self.country)

    def test_branch_waives_foreign_delivery_and_warns_on_manual_mismatch(self):
        quote = SimpleNamespace(rental_country='CZ', pickup_city=self.city.name, return_city=self.city.name, cross_border_requested=False)
        context = route_context(quote, self.supplier)
        self.assertFalse(context['cross_border'])
        self.assertFalse(context['prepayment'])
        self.assertEqual(context['local_sides'], {'pickup', 'return'})
        quote.rental_country = 'PL'
        self.assertTrue(route_context(quote, self.supplier)['warnings'])
        self.assertEqual(quote.rental_country, 'PL')

    def test_country_name_and_targeted_wording_come_from_data(self):
        self.assertEqual(location_country(self.city.name), 'CZ')
        self.country.wording = {'outside Poland': 'TEST-COUNTRY-TEXT'}
        self.country.save()
        self.assertEqual(localize_country_text('outside Poland; Poland airport', SimpleNamespace(rental_country='CZ')),
                         'TEST-COUNTRY-TEXT; Poland airport')

    def test_standard_polish_cities_and_all_configured_foreign_cities_have_countries(self):
        self.assertEqual(location_country('Warszawa'), 'PL')
        self.assertEqual(location_country('Kraków'), 'PL')
        self.assertEqual(location_country('TEST city, Hungary'), 'HU')
        self.assertEqual(location_country('TEST city, Slovakia'), 'SK')
