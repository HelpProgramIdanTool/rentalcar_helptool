"""Prepare the existing cross-border guide in the shared practical-guide style."""
import json
import re
from pathlib import Path
import prepare_winter_publication as winter

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'wordpress/prc-bilingual/content/go-abroad-he.html').read_text(encoding='utf-8')
css = re.search(r'<style>(.*?)</style>', winter.payload['content'], re.S).group(1)
payload = dict(title='יציאה מפולין עם רכב שכור — ביטוח, מסמכים וכבישי אגרה',
 content='<style>'+css+'</style><div class="prc-winter-page" lang="he" dir="rtl"><div class="winter-page">'+source+'</div></div>',
 excerpt='מתכננים לצאת מפולין ברכב שכור? אישור החברה, ביטוח וסיוע בחו״ל, מסמכים, וינייטות וקישורי תשלום רשמיים — המדריך של עידן.')
path = ROOT/'output/website-review/go-abroad-publication.json'
path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
print(path)
