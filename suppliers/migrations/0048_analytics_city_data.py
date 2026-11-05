import unicodedata
from django.db import migrations


def populate(apps, schema_editor):
    City=apps.get_model('suppliers','AnalyticsCity')
    Location=apps.get_model('suppliers','SupplierLocation')
    OfferCity=apps.get_model('suppliers','OfferCity')
    # Initial business data only. All aliases remain editable in the admin.
    seeds=[
        ('Kraków','Краков','Poland',['Krakow','Kraków Balice','Balice','Краков']),
        ('Warszawa','Варшава','Poland',['Warsaw','Warszawa-Chopin','Варшава']),
        ('Modlin','Модлин','Poland',['Nowy Dwór Mazowiecki','Nowy Dwor Mazowiecki','Warsaw Modlin','Warszawa Modlin','Модлин']),
        ('Wrocław','Вроцлав','Poland',['Wroclaw','Вроцлав']),
        ('Gdańsk','Гданьск','Poland',['Gdansk','Гданьск']),
        ('Katowice','Катовице','Poland',['Katowice Pyrzowice','Pyrzowice','Катовице']),
        ('Łódź','Лодзь','Poland',['Lodz','Łodz','Лодзь']),
        ('Poznań','Познань','Poland',['Poznan','Познань']),
        ('Toruń','Торунь','Poland',['Torun','Торунь']),
        ('Rzeszów','Жешув','Poland',['Rzeszow','Жешув']),
        ('Olsztyn','Ольштын','Poland',['Olsztyn Szymany','Szymany','Ольштын']),
        ('Szczecin','Щецин','Poland',['Szczecin Goleniów','Goleniów','Goleniow','Щецин']),
        ('Prague','Прага','Czech Republic',['Praha','Prague Airport','Прага']),
        ('Pardubice','Пардубице','Czech Republic',['Pardubice Airport','Пардубице']),
        ('Brno','Брно','Czech Republic',['Брно']),
        ('Ostrava','Острава','Czech Republic',['Острава']),
        ('Vienna','Вена','Austria',['Wien','Вена']),
        ('Budapest','Будапешт','Hungary',['Будапешт']),
        ('Bratislava','Братислава','Slovakia',['Братислава']),
        ('Berlin','Берлин','Germany',['Берлин']),
        ('Vilnius','Вильнюс','Lithuania',['Вильнюс','Вильно']),
    ]
    def fold(text):
        return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold().replace('ł','l')) if not unicodedata.combining(c))
    represented=set()
    for name,label,country,aliases in seeds:
        City.objects.get_or_create(name=name,defaults={'label':label,'country':country,'aliases':aliases})
        represented.update(fold(v) for v in [name,label,*aliases])
    for item in [*Location.objects.values('city','country'),
                 *({'city':c.name,'country':c.country} for c in OfferCity.objects.all())]:
        name=item['city'].strip()
        if name and fold(name) not in represented:
            City.objects.get_or_create(name=name,defaults={'label':name,'country':item['country'],'aliases':[]})
            represented.add(fold(name))


class Migration(migrations.Migration):
    dependencies=[('suppliers','0047_analyticscity')]
    operations=[migrations.RunPython(populate,migrations.RunPython.noop)]
