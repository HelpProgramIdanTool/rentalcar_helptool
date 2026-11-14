from django.db import migrations


def seed(apps, schema_editor):
    Country = apps.get_model('suppliers', 'RentalCountry')
    notice = {'English': 'Payment must be received before vehicle handover.',
              'Hebrew': 'יש לקבל את התשלום מראש, לפני מסירת הרכב.',
              'Russian': 'Оплата должна быть получена заранее, до передачи автомобиля.',
              'Polish': 'Płatność musi zostać otrzymana przed wydaniem samochodu.'}
    for code, name, aliases, active in [
        ('PL', 'Польша', ['Poland', 'Polska', 'פולין'], True),
        ('CZ', 'Чехия', ['Czechia', 'Czech Republic', 'Česko', 'צ׳כיה', 'צכיה'], True),
        ('SK', 'Словакия', ['Slovakia', 'Slovensko', 'סלובקיה'], False),
        ('HU', 'Венгрия', ['Hungary', 'Magyarország', 'הונגריה'], False),
        ('AT', 'Австрия', ['Austria', 'Österreich', 'אוסטריה'], False),
        ('DE', 'Германия', ['Germany', 'Deutschland', 'גרמניה'], False),
        ('LT', 'Литва', ['Lithuania', 'Lietuva', 'ליטא'], False),
    ]:
        names = {'PL': ('Poland', 'Polska', 'פולין'), 'CZ': ('Czechia', 'Czechy', 'צ׳כיה'),
                 'SK': ('Slovakia', 'Słowacja', 'סלובקיה'), 'HU': ('Hungary', 'Węgry', 'הונגריה'),
                 'AT': ('Austria', 'Austria', 'אוסטריה'), 'DE': ('Germany', 'Niemcy', 'גרמניה'),
                 'LT': ('Lithuania', 'Litwa', 'ליטא')}[code]
        Country.objects.get_or_create(code=code, defaults=dict(name=name, aliases=aliases,
            localized_names=dict(English=names[0], Polish=names[1], Hebrew=names[2], Russian=name,
                English_label='Rental country', Polish_label='Kraj wynajmu', Hebrew_label='מדינת ההשכרה', Russian_label='Страна аренды'),
            is_active=active, prepayment_text=notice, wording={
                'outside Poland': 'outside Czechia', 'travel outside Poland': 'travel outside Czechia',
                'מחוץ לפולין': 'מחוץ לצ׳כיה', 'יציאה מפולין': 'יציאה מצ׳כיה',
                'за пределы Польши': 'за пределы Чехии',
            } if code == 'CZ' else {}))
    Supplier = apps.get_model('suppliers', 'Supplier')
    City = apps.get_model('suppliers', 'OfferCity')
    for name in ('Warszawa', 'Kraków', 'Katowice', 'Gdańsk', 'Lublin', 'Łódź',
                 'Modlin', 'Olsztyn', 'Poznań', 'Rzeszów', 'Szczecin', 'Wrocław',
                 'Radom', 'Bydgoszcz'):
        City.objects.get_or_create(name=name, defaults={
            'label': name, 'country': 'Poland', 'cross_border_required': False})
    Branch = apps.get_model('suppliers', 'SupplierLocalBranch')
    supplier = Supplier.objects.filter(supplier_name__iexact='Car Free').first()
    if supplier:
        city, _ = City.objects.get_or_create(name='Prague', defaults={
            'label': 'פראג', 'country': 'Czechia', 'cross_border_required': True})
        Branch.objects.get_or_create(supplier=supplier, city=city,
            defaults={'country': Country.objects.get(code='CZ')})


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0055_rentalcountry_supplierlocalbranch')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
