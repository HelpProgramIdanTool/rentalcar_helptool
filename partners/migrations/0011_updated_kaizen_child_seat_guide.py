from django.db import migrations


def update_guide(apps, schema_editor):
    Configuration = apps.get_model('partners', 'PortalConfiguration')
    config = Configuration.objects.first()
    if not config:
        return
    content = dict(config.content or {})
    guides = dict(content.get('child_seat_guides', {}))
    guides['01'] = ['Kaizen', 'private:Rules_for_transporting_children_KaizenRent_EN.pdf', 'Kaizen-child-seats.pdf']
    content['child_seat_guides'] = guides
    config.content = content
    config.save(update_fields=['content'])


class Migration(migrations.Migration):
    dependencies = [('partners', '0010_child_seat_guides')]
    operations = [migrations.RunPython(update_guide, migrations.RunPython.noop)]
