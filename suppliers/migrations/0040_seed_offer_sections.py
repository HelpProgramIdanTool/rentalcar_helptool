from django.db import migrations


def seed(apps, schema_editor):
    Group = apps.get_model('suppliers', 'VehicleGroup')
    for group in Group.objects.all():
        text = ' '.join([group.group_name, group.customer_name_en, group.category]).upper()
        if any(word in text for word in ('PREMIUM', 'LUXURY', 'LUX', 'ПРЕМИУМ')):
            section = 'premium'
        elif group.body_type in ('VAN', 'MINIVAN') or any(word in text for word in ('VAN', '9 SEAT', '8 SEAT', 'BUS')):
            section = 'vans'
        elif group.body_type == 'SUV' or any(word in text for word in ('SUV', 'CROSS')):
            section = 'crossovers'
        else:
            section = 'cars'
        group.offer_section = section
        group.save(update_fields=['offer_section'])
    labels = {
        'Russian': ['Легковые: седаны, универсалы и хетчбэки', 'Кроссоверы', 'Премиум', 'Минивэны и микроавтобусы'],
        'English': ['Cars: sedans, estates and hatchbacks', 'SUVs and crossovers', 'Premium', 'Minivans and passenger vans'],
        'Polish': ['Samochody: sedany, kombi i hatchbacki', 'SUV-y i crossovery', 'Premium', 'Minivany i busy'],
        'Hebrew': ['מכוניות: סדאן, סטיישן והאצ׳בק', 'רכבי פנאי וקרוסאוברים', 'פרימיום', 'מיניוואנים ורכבי נוסעים גדולים'],
    }
    Template = apps.get_model('quotes', 'QuoteTemplate')
    for template in Template.objects.all():
        presentation = dict(template.presentation or {})
        order = ['cars', 'crossovers', 'premium', 'vans']
        presentation.setdefault('section_order', order)
        presentation.setdefault('section_labels', dict(zip(order, labels.get(template.language, labels['English']))))
        template.presentation = presentation
        template.save(update_fields=['presentation'])


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0039_vehiclegroup_offer_section'), ('quotes', '0023_polish_offer')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
