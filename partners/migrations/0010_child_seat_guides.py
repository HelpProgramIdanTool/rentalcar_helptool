from django.db import migrations


def seed(apps, schema_editor):
    Configuration = apps.get_model('partners', 'PortalConfiguration')
    config = Configuration.objects.first()
    if not config:
        config = Configuration.objects.create()
    content = dict(config.content or {})
    guides = content.setdefault('child_seat_guides', {})
    for key, values in {
        '01': ['Kaizen', 'ריכוז חוקים אודות כיסאות בטיחות ובוסטרים.pdf', 'Kaizen-child-seats.pdf'],
        '02': ['One Rent', 'Rules for transporting children by car in Poland.pdf', 'One-Rent-child-seats.pdf'],
        'MM Cars': ['MM Cars', 'private:MM_Cars_Rental_Rules_Child_Seat.pdf', 'MM-Cars-child-seats.pdf'],
    }.items():
        guides.setdefault(key, values)
    config.content = content
    config.save(update_fields=['content'])


class Migration(migrations.Migration):
    dependencies = [('partners', '0009_offer_company_comparison')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
