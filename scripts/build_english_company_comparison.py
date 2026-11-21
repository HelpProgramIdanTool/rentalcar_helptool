"""Prepare the English article using the same seeded comparison facts as offers."""
import copy
import importlib
import json
import sys
from html import escape
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

class Row(SimpleNamespace):
    def save(self, **kwargs):
        pass

def build():
    initial = importlib.import_module('partners.migrations.0002_owner_approved_comparison')
    data = copy.deepcopy(initial.DATA)
    summaries = [Row(**row) for row in data['summaries']]
    config = Row(content=data['content'])
    models = {'SupplierSummary': SimpleNamespace(objects=SimpleNamespace(all=lambda: summaries)),
              'PortalConfiguration': SimpleNamespace(objects=SimpleNamespace(all=lambda: [config]))}
    apps = SimpleNamespace(get_model=lambda app, model: models[model])
    importlib.import_module('partners.migrations.0008_foreign_handover_and_abroad_support').seed(apps, None)
    importlib.import_module('partners.migrations.0009_offer_company_comparison').seed(apps, None)
    labels = config.content['offer_comparison']['English']
    header = '<tr><th>What to compare</th>' + ''.join('<th>'+escape(s.name)+'</th>' for s in summaries) + '</tr>'
    rows = ''.join('<tr><th>'+escape(label)+'</th>' + ''.join('<td>'+escape(s.facts['translations']['English'].get(key, labels['unknown']))+'</td>' for s in summaries) + '</tr>' for key,label in zip(labels['keys'], labels['columns'][1:]))
    content = '''<p>Four rental companies, one personal point of contact. I am Idan. This is a rental agency service, not another automated price-comparison engine. I explain the differences, coordinate your booking and help you deal with the company if something goes wrong.</p>
<h2>The standard behind my offers</h2><p>My relationships and booking volume give me direct contacts at these companies. Whichever company you choose, you book as my client, with personal VIP support and priority when I follow up on your behalf. This is not a promise of an instant response, a free upgrade or a particular car model.</p>
<p>My offers include insurance with zero excess covering theft, glass and wheels, subject to the rental conditions. All companies provide season-appropriate tyres. The quotation explains the total price, deposit and selected extras before you commit. A security deposit and insurance excess are different things: zero excess does not automatically mean no deposit.</p>
<h2>Compare the practical differences</h2><div style="overflow-x:auto"><table class="prc-company-comparison"><thead>''' + header + '</thead><tbody>' + rows + '''</tbody></table></div>
<p>Kaizen and Car Free have desks at most airports. Collection at the terminal is included with all four companies under my offers. A desk and a vehicle meeting point are not necessarily the same place: follow the instructions in your confirmation. Return arrangements for One Rent and MM Cars depend on the airport.</p>
<h2>Which company fits your trip?</h2><h3>Kaizen Rent</h3><p>A useful option for a broad network in Poland and terminal collection and return. Vehicle age depends on the group; there is no blanket promise here that every car is under two years old. Vehicles must be collected and returned in Poland. Driving abroad may still be authorised separately. <a href="/kaizen-rent/">Read the existing company page (Hebrew)</a>.</p>
<h3>Car Free</h3><p>A modern fleet with vehicles up to two years old under my agreed terms, desks at most airports and terminal collection and return. Return the same fuel level you received, rather than assuming a full-to-full policy. Car Free has a Prague branch: collection and return in Prague constitute a Czech rental, so travel abroad means leaving Czechia. Prague–Warsaw is an international route requiring separate approval. <a href="/car-free/">Practical company guide (Hebrew)</a>.</p>
<h3>One Rent</h3><p>Vehicles up to two years old under my agreed terms, with family, SUV and premium groups to compare. Fuel is full to full. Terminal return depends on the airport. Optional GPS navigation cannot be ordered from One Rent; built-in equipment depends on the vehicle specification. <a href="/one-rent/">Read the existing company page (Hebrew)</a>.</p>
<h3>MM Cars</h3><p>Vehicles up to two years old under my agreed terms, with GPS in every car according to the company's commitment. Fuel is full to full. Collection is at the terminal; return instructions depend on the airport. Check any specific navigation language or phone-connection requirement before booking. <a href="/mm-cars/">Practical company guide (Hebrew)</a>.</p>
<h2>Foreign handover and driving abroad are different services</h2><p>Car Free, One Rent and MM Cars can arrange collection or return outside Poland with prior agreement. Availability, delivery costs and payment requirements must be confirmed separately. Foreign collection generally requires advance payment; a local rental at Car Free's Prague branch follows its own confirmed terms. Kaizen handover is in Poland only. Permission to drive abroad does not itself include international delivery.</p>
<h2>What happens if the car is disabled outside Poland?</h2><p>For an approved cross-border trip included in my package, a covered incident includes a replacement car in the same category and transport of the damaged car from the incident location abroad back to Poland, with no additional charge for those services, subject to the rental, coverage and reporting conditions. Contact me and the assistance service using your confirmation instructions before arranging services independently.</p>
<p>When booking directly on a rental company's own website, permission to cross the border and insurance cover do not by themselves guarantee a replacement abroad or towing back to Poland. Some companies offer additional assistance packages. Compare the package actually purchased, not just the phrase “travel abroad allowed”.</p>
<h2>Wide insurance cover still has exclusions</h2><p>Fines, excessive interior dirt, non-covered interior damage, deliberate acts, misuse, driving under the influence and breaches of the rental agreement are not made covered by a zero-excess package. Wrong fuel or lost keys may also fall outside the protection. The confirmed policy and contract govern the details, exclusions and reporting requirements.</p>
<h2>A vehicle category is not a guaranteed model</h2><p>I compare groups by practical needs: passengers, luggage space, transmission and vehicle type. Named models are examples of the category. Tell me if a particular feature is essential; it is guaranteed only when explicitly confirmed. State every driver's age and licence experience, child-seat requirements, flight number and proposed countries before booking.</p>
<p><a href="/english/request-quote/">Request a personal quotation</a> · <a href="/english/car-rental-insurance/">Insurance guide</a> · <a href="/english/car-rental-deposit/">Deposit guide</a> · <a href="/english/driving-rental-car-abroad/">Driving abroad</a></p>'''
    content = '<style>.prc-company-comparison{border-collapse:collapse;width:100%;font-size:14px;line-height:1.5}.prc-company-comparison th,.prc-company-comparison td{border:1px solid #d3deea;padding:9px;text-align:left;vertical-align:top}.prc-company-comparison thead th{background:#163960;color:white}@media(max-width:600px){.prc-company-comparison{font-size:12px}.prc-company-comparison th,.prc-company-comparison td{padding:5px}}</style>' + content
    path = ROOT / 'wordpress/prc-bilingual/content/en-pages.json'
    pages = json.loads(path.read_text(encoding='utf-8'))
    page = next(p for p in pages if p['key'] == 'companies')
    page['content'] = content
    page['meta_description'] = 'Compare Kaizen, Car Free, One Rent and MM Cars: vehicle age, fuel, terminal service and cross-border support, with personal help from Idan.'
    path.write_text(json.dumps(pages, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    target = ROOT / 'output/website-review/english-companies-publication.json'
    target.write_text(json.dumps(page, ensure_ascii=False), encoding='utf-8')
    print('English article prepared from shared comparison seeds.')
    return config, summaries

if __name__ == '__main__':
    build()
