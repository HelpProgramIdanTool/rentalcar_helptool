"""Export public city names for the isolated design; never exports prices/customers."""
import os
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from quotes.forms import FirstInquiryForm
from suppliers.models import OfferCity

labels = {'Warszawa':'ורשה','Kraków':'קרקוב','Katowice':'קטוביץ','Gdańsk':'גדנסק',
          'Lublin':'לובלין','Łódź':'לודז׳','Modlin':'מודלין','Olsztyn':'אולשטין',
          'Poznań':'פוזנן','Rzeszów':'ז׳שוב','Szczecin':'שצ׳צ׳ין','Wrocław':'ורוצלב',
          'Radom':'ראדום','Bydgoszcz':'בידגושץ','Prague':'פראג','Pardubice':'פרדוביצה',
          'Budapest':'בודפשט','Vienna':'וינה','Bratislava':'ברטיסלבה','Berlin':'ברלין',
          'Vilnius':'וילנה','Ostrava':'אוסטרבה','Brno':'ברנו','Lubin':'לובין'}
cities = {name:{'name':name,'label':labels.get(name,name),'country':'Czech Republic' if name in ('Prague','Pardubice') else 'Poland'}
          for name,label in FirstInquiryForm.CITY_CHOICES if name and name!='OTHER'}
for city in OfferCity.objects.filter(is_active=True):
    cities[city.name]={'name':city.name,'label':labels.get(city.name,city.name),'country':city.country}
target=Path(__file__).resolve().parents[1]/'prototype/partner-portal-v2/cities.js'
target.write_text('// Public cities: operator fallback list plus active configured cities. No prices.\nwindow.PRC_DESIGN_CITIES = '+json.dumps(list(cities.values()),ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
print(f'Exported {len(cities)} public city names.')
