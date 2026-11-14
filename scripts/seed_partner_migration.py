"""Write an immutable migration snapshot of the owner-approved portal wording."""
import json
from pathlib import Path
from pprint import pformat

data=json.loads(Path('partners/initial_content.json').read_text(encoding='utf-8'))
text='from django.db import migrations\n\nDATA = '+pformat(data,width=110,sort_dicts=False)+'''

def seed(apps, schema_editor):
    Config = apps.get_model('partners', 'PortalConfiguration')
    Summary = apps.get_model('partners', 'SupplierSummary')
    Config.objects.get_or_create(pk=1, defaults={'content':DATA['content']})
    for index, row in enumerate(DATA['summaries']):
        Summary.objects.get_or_create(name=row['name'], defaults={'facts':row['facts'], 'display_order':index})

class Migration(migrations.Migration):
    dependencies = [('partners','0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
'''
Path('partners/migrations/0002_owner_approved_comparison.py').write_text(text,encoding='utf-8')
print('Wrote immutable owner-approved comparison migration')
