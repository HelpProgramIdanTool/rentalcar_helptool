"""Prepare the approved contact-responsibility guide using centered guide styles."""
import json
import re
from pathlib import Path
import prepare_winter_publication as winter

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'wordpress/prc-bilingual/content/contact-service-he.html').read_text(encoding='utf-8')
css = re.search(r'<style>(.*?)</style>', winter.payload['content'], re.S).group(1)
payload = dict(title='שירות לקוחות ואיש קשר — למי פונים ובאיזה נושא?',
 content='<style>'+css+'</style><div class="prc-winter-page" lang="he" dir="rtl"><div class="winter-page">'+source+'</div></div>',
 excerpt='מוקד חברת ההשכרה פועל 24/7 לתפעול ותיאומים; עידן מלווה במקרים חריגים. בכל פנייה מציינים מספר הזמנה, שם חברה ומיקום נוכחי.')
path = ROOT/'output/website-review/contact-service-publication.json'
path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
print(path)
