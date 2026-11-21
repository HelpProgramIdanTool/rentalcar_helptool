from django.db import migrations

WORDING = {
    'מחוץ לגבולות פולין': 'מחוץ לגבולות צ׳כיה',
    'מחוץ לפולין': 'מחוץ לצ׳כיה',
    'יציאה מפולין': 'יציאה מצ׳כיה',
    'השכרת רכב בפולין': 'השכרת רכב בצ׳כיה',
    'השכרת הרכב בפולין': 'השכרת הרכב בצ׳כיה',
    'outside of Poland': 'outside Czechia',
    'outside Poland': 'outside Czechia',
    'rental in Poland': 'rental in Czechia',
    'Rental in Poland': 'Rental in Czechia',
    'за пределами Польши': 'за пределами Чехии',
    'за пределы Польши': 'за пределы Чехии',
    'выезд из Польши': 'выезд из Чехии',
    'аренда в Польше': 'аренда в Чехии',
    'poza Polskę': 'poza Czechy',
    'poza Polską': 'poza Czechami',
    'wyjazd z Polski': 'wyjazd z Czech',
    'wynajem w Polsce': 'wynajem w Czechach',
}

def seed(apps, schema_editor):
    Country = apps.get_model('suppliers','RentalCountry')
    for country in Country.objects.filter(code='CZ'):
        country.wording={**WORDING, **country.wording}
        country.save(update_fields=['wording'])

class Migration(migrations.Migration):
    dependencies=[('suppliers','0061_czech_local_offer_mode')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
