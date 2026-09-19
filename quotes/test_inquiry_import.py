from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .inquiry_import import parse_inquiry, suitable_group
from .models import Quote
from suppliers.models import Supplier, VehicleGroup


SAMPLE = '''מספר פנייה: TEST-123
שם: Test Person
טלפון / וואטסאפ: 123456789
דוא״ל: test@example.com
כל נהג מעל גיל 24 ועם לפחות שנה רישיון: כן
קבלת הרכב:
עיר: קרקוב
מקום: שדה תעופה
תאריך: 2026-09-26
שעה: 15:00
החזרת הרכב:
עיר: קרקוב
מקום: שדה תעופה
תאריך: 2026-10-03
שעה: 11:30
מספר נוסעים כולל הנהג: 6
מספר מזוודות משוער: 5
תיבת הילוכים: אוטומטית בלבד
קבוצות רכב שנבחרו:
- רכב סטיישן
- רכב של 7 מקומות
- רכב 8/9 מקומות
יציאה מחוץ לפולין:
לא
כיסאות / בוסטרים: לא
מספר כיסאות / בוסטרים:
GPS: לא
שרשראות שלג: לא
הערות הלקוח:
ילדים; מביאים כיסא תינוק אחד
'''


class ParserTests(SimpleTestCase):
    def test_dates_contacts_and_original_preserved(self):
        data, requirements, warnings = parse_inquiry(SAMPLE)
        self.assertEqual(data['pickup_date'], '26-09-2026')
        self.assertEqual(data['return_time'], '11:30')
        self.assertEqual(data['pickup_city'], 'Kraków')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['customer_notes'], SAMPLE)
        self.assertEqual(requirements['passengers'], 6)
        self.assertEqual(data['extra_choices'], [])
        self.assertFalse(data['cross_border_requested'])
        self.assertTrue(any('кресла' in w for w in warnings))

    def test_explicit_extras_and_cross_border(self):
        data, _, _ = parse_inquiry(SAMPLE.replace('כיסאות / בוסטרים: לא', 'כיסאות / בוסטרים: כן').replace('מספר כיסאות / בוסטרים:', 'מספר כיסאות / בוסטרים: 2').replace('יציאה מחוץ לפולין:\nלא', 'יציאה מחוץ לפולין:\nכן'))
        self.assertEqual(data['extra_choices'], ['CHILD_SEAT'])
        self.assertEqual(data['child_seat_quantity'], '2')
        self.assertTrue(data['cross_border_requested'])

    def test_bad_date_not_guessed(self):
        data, _, warnings = parse_inquiry(SAMPLE.replace('2026-09-26', 'tomorrow'))
        self.assertEqual(data['pickup_date'], '')
        self.assertTrue(any('даты' in w for w in warnings))

    def test_january_dates_four_drivers_and_large_suv(self):
        sample = SAMPLE.replace('2026-09-26', '2027-01-20').replace('2026-10-03', '2027-01-23').replace('כולל הנהג: 6', 'כולל הנהג: 4')
        sample = sample[:sample.index('קבוצות רכב שנבחרו:')] + 'קבוצות רכב שנבחרו:\n- קראסאובר SUV גדול\n- רכב פרמיום SUV גדול\nהערות הלקוח:\n4 נהגים.'
        data, requirements, _ = parse_inquiry(sample)
        self.assertEqual(data['pickup_date'], '20-01-2027')
        self.assertEqual(data['return_date'], '23-01-2027')
        self.assertEqual(data['driver_count'], 4)
        for name, body, expected in [('SUV LARGE', 'SUV', True), ('SUV MEDIUM', 'SUV', False), ('SUV SMALL', 'SUV', False), ('Sedan', 'SEDAN', False)]:
            group = SimpleNamespace(group_name=name, body_type=body, seats=None, transmission='AUTOMATIC')
            self.assertEqual(suitable_group(group, requirements), expected)

    def test_selection_excludes_small_manual_unknown(self):
        _, requirements, _ = parse_inquiry(SAMPLE)
        for seats, transmission, expected in [(5,'AUTOMATIC',False),(9,'MANUAL',False),(None,'AUTOMATIC',False),(7,'UNKNOWN',False),(7,'AUTOMATIC',True),(9,'AUTOMATIC',True)]:
            with self.subTest(seats=seats, transmission=transmission):
                self.assertEqual(suitable_group(SimpleNamespace(seats=seats,transmission=transmission,body_type='VAN'), requirements), expected)

    def test_standard_sedan_request_excludes_large_premium_and_manual_groups(self):
        requirements = {
            'passengers': 2, 'automatic': True, 'manual': False,
            'categories': ['רכב סטנדרטי סדאן', 'רכב היברידי'],
        }
        candidates = [
            ('C Automatic Sedan', 'SEDAN', 'AUTOMATIC', True),
            ('D Premium Sedan', 'SEDAN', 'AUTOMATIC', False),
            ('E', 'SEDAN', 'AUTOMATIC', False),
            ('SUV big', 'SUV', 'AUTOMATIC', False),
            ('9 seat van', 'VAN', 'AUTOMATIC', False),
            ('C Manual Sedan', 'SEDAN', 'MANUAL', False),
        ]
        for name, body, transmission, expected in candidates:
            with self.subTest(name=name):
                group = SimpleNamespace(group_name=name, body_type=body, seats=5,
                                        transmission=transmission, category='')
                self.assertEqual(suitable_group(group, requirements), expected)

    def test_small_or_medium_suv_request_excludes_big_and_premium(self):
        requirements = {
            'passengers': 2, 'automatic': True, 'manual': False,
            'categories': ['קראסאובר SUV קטן', 'קראסאובר SUV בינוני'],
        }
        candidates = [
            ('SUV small AT', 'SUV_SMALL_AUTO', 'AUTOMATIC', True),
            ('SUV medium AT', 'SUV_MEDIUM_AUTO', 'AUTOMATIC', True),
            ('SUV large AT', 'SUV_BIG_AUTO', 'AUTOMATIC', False),
            ('SUV Premium small AT', 'PREMIUM_SUV_AUTO', 'AUTOMATIC', False),
            ('SUV medium manual', 'SUV_MEDIUM_AUTO', 'MANUAL', False),
        ]
        for name, code, transmission, expected in candidates:
            with self.subTest(name=name):
                classes = SimpleNamespace(all=lambda: [SimpleNamespace(code=code)])
                group = SimpleNamespace(group_name=name, body_type='SUV', seats=5,
                                        transmission=transmission, category='', comparison_classes=classes)
                self.assertEqual(suitable_group(group, requirements), expected)

    def test_small_suv_or_premium_medium_keeps_each_requested_tier(self):
        requirements = {
            'passengers': 2, 'automatic': True, 'manual': False,
            'categories': ['קראסאובר SUV קטן', 'רכב פרמיום SUV בינוני'],
        }
        candidates = [
            ('SUV small AT', 'SUV_SMALL_AUTO', True),
            ('SUV medium AT', 'SUV_MEDIUM_AUTO', False),
            ('SUV Premium medium AT', 'PREMIUM_SUV_AUTO', True),
            ('SUV Premium large AT', 'PREMIUM_SUV_AUTO', False),
        ]
        for name, code, expected in candidates:
            with self.subTest(name=name):
                classes = SimpleNamespace(all=lambda: [SimpleNamespace(code=code)])
                group = SimpleNamespace(group_name=name, body_type='SUV', seats=5,
                                        transmission='AUTOMATIC', category='', comparison_classes=classes)
                self.assertEqual(suitable_group(group, requirements), expected)

    def test_snow_chain_recommendation_is_a_question_not_a_purchase(self):
        sample = SAMPLE.replace('שרשראות שלג: לא', 'שרשראות שלג: צריך המלצה')
        data, _, warnings = parse_inquiry(sample)
        self.assertNotIn('SNOW_CHAINS', data['extra_choices'])
        self.assertTrue(any('цеп' in warning for warning in warnings))

    def test_hotel_pickup_and_airport_return_keep_their_places(self):
        sample = SAMPLE.replace('מקום: שדה תעופה', 'מקום: כתובת המלון שלכם', 1)
        data, _, warnings = parse_inquiry(sample)
        self.assertEqual(data['pickup_service'], 'ADDRESS')
        self.assertEqual(data['pickup_address'], 'כתובת המלון שלכם')
        self.assertEqual(data['return_service'], 'AIRPORT')
        self.assertEqual(data['return_address'], '')
        self.assertTrue(any('отеля' in warning for warning in warnings))

    def test_alternate_hebrew_spelling_of_krakow_fills_both_city_fields(self):
        data, _, _ = parse_inquiry(SAMPLE.replace('קרקוב', 'קראקוב'))
        self.assertEqual(data['pickup_city'], 'Kraków')
        self.assertEqual(data['return_city'], 'Kraków')


class ImportViewTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='import-test'))

    def test_import_no_customer_quote_or_mail_created(self):
        supplier = Supplier.objects.create(supplier_code='TEST', supplier_name='Test supplier')
        other = Supplier.objects.create(supplier_code='OTHER', supplier_name='Other supplier')
        group = VehicleGroup.objects.create(supplier=supplier, group_code='T', group_name='Test van', seats=9, transmission='AUTOMATIC')
        response = self.client.post(reverse('quotes:import_inquiry'), {'text': SAMPLE})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['fields']['vehicle_groups'], [group.pk])
        self.assertIn(other.pk, response.json()['fields']['suppliers'])
        self.assertEqual(Quote.objects.count(), 0)
        fields = response.json()['fields']
        fields['imported_inquiry'] = '1'
        fields.pop('cross_border_requested')
        response = self.client.post(reverse('quotes:new_inquiry'), fields)
        quote = Quote.objects.get()
        self.assertRedirects(response, reverse('quotes:calculate_quote', args=[quote.quote_number]))
        self.assertEqual(quote.rental_days, 7)
        self.assertEqual(quote.status, 'DRAFT')
        self.assertEqual(quote.customer_notes, SAMPLE.strip())

    def test_invalid_and_anonymous(self):
        self.assertEqual(self.client.post(reverse('quotes:import_inquiry'), {'text':'hello'}).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.post(reverse('quotes:import_inquiry'), {'text':SAMPLE}).status_code, 302)
