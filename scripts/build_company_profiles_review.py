"""Build linked Hebrew company drafts for review, without changing WordPress."""
from html import escape
from pathlib import Path
from build_rental_companies_review import STYLE, COMPANIES, asset, build

OUT = Path(__file__).resolve().parents[1] / 'output/website-review'
LINKS = {'kaizen': 'https://poland-rent-car.com/kaizen-rent/',
         'onerent': 'https://poland-rent-car.com/one-rent/',
         'carfree': 'car-free-review.html', 'mmcars': 'mm-cars-review.html'}

PROFILES = {
 'carfree': {
  'title': 'Car Free — מידע מעשי לפני הזמנת רכב',
  'lead': 'צי חדיש, שירות בטרמינל ואפשרות לאיסוף בפראג. כך בודקים שההצעה מתאימה למסלול שלכם, ומה חשוב לדעת לפני קבלת הרכב.',
  'facts': [('גיל הרכב', 'עד שנתיים, במסגרת התנאים שסוכמו עם החברה'), ('קבלה והחזרה', 'בטרמינל; דלפקים ברוב נמלי התעופה'), ('מדיניות דלק', 'מחזירים באותו מפלס שבו התקבל הרכב'), ('מחוץ לפולין', 'אפשרות לקבלה ולהחזרה, בתיאום ואישור מראש')],
  'sections': [
   ('למי החברה עשויה להתאים?', 'למי שמעדיף רכב חדיש ושירות נוח בנמל התעופה. אפשר לבדוק קבוצות שונות לפי מספר הנוסעים, הכבודה והמסלול. הדגם שמופיע בהצעה מייצג את הקבוצה; דגם מסוים מובטח רק אם הדבר אושר במפורש.'),
   ('קבלת הרכב והחזרתו', 'קבלת הרכב והחזרתו מתבצעות בטרמינל במסגרת ההצעה שלי. המיקום המדויק והוראות המפגש מופיעים באישור ההזמנה. מוסרים מראש מספר טיסה ופרטי קשר זמינים. אם הטיסה מתעכבת או מקום המפגש אינו ברור, פונים אליי לפני שמשנים את התוכנית.'),
   ('דלק: אותו מפלס, לא בהכרח מיכל מלא', 'ב-Car Free מחזירים את הרכב עם אותה כמות דלק שקיבלתם. מצלמים את מד הדלק בקבלה ובהחזרה ובודקים שהמפלס נרשם במסמכי המסירה. אין צורך להניח שהמיכל חייב להיות מלא אם הרכב לא נמסר כך.'),
   ('פראג: מתי זו השכרה בצ׳כיה?', 'ל-Car Free יש סניף בפראג. כאשר גם הקבלה וגם ההחזרה בפראג, מדובר בהשכרה מקומית בצ׳כיה. במקרה הזה, יציאה לחו״ל פירושה יציאה מצ׳כיה. מסלול פראג–ורשה או ורשה–פראג הוא מסלול בין מדינות ומחייב בדיקה ואישור מתאימים.'),
   ('קבלה במדינה אחרת אינה רק אישור מעבר גבול', 'קבלה או החזרה מחוץ לפולין אפשריות בתיאום מראש. יש לבדוק בנפרד את נקודת המסירה, הזמינות, העלות ותנאי התשלום. בקבלה מחוץ לפולין עשוי להידרש תשלום מראש; השכרה מקומית בסניף פראג נבדקת לפי תנאי ההצעה שלה. אין להסיק שמחיר אישור נסיעה לחו״ל כולל גם מסירה במדינה אחרת.'),
   ('מה חשוב לבדוק בהצעה?', 'בודקים את הקבוצה, מספר המקומות והכבודה, סכום הפיקדון, תנאי הכרטיס ותוספות שאושרו. החזרה בעיר אחרת או במדינה אחרת דורשת בדיקה נפרדת. המחירים והתנאים הקובעים הם אלו שבהצעה המאושרת, ולא מחיר כללי שמופיע באתר אחר.')]
 },
 'mmcars': {
  'title': 'MM Cars — מידע מעשי לפני הזמנת רכב',
  'lead': 'רכבים עד גיל שנתיים ו-GPS בכל רכב לפי התחייבות החברה. מידע ברור על המסירה, ההחזרה והפרטים שחשוב לאשר מראש.',
  'facts': [('גיל הרכב', 'עד שנתיים, במסגרת התנאים שסוכמו עם החברה'), ('ניווט', 'החברה מבטיחה GPS בכל רכב'), ('מדיניות דלק', 'מלא למלא'), ('מחוץ לפולין', 'אפשרות לקבלה ולהחזרה, בתיאום ואישור מראש')],
  'sections': [
   ('למי החברה עשויה להתאים?', 'למי שמחפש רכב חדיש ומייחס חשיבות לניווט ברכב. אפשר לבדוק קבוצות משפחתיות, SUV ופרמיום בהתאם לזמינות ולצרכים. הבחירה נעשית לפי הקבוצה והמפרט בהצעה; תמונה או שם דגם לדוגמה אינם התחייבות לדגם מסוים.'),
   ('קבלת הרכב בטרמינל, ההחזרה לפי נמל התעופה', 'קבלת הרכב היא בטרמינל במסגרת ההצעה שלי. מקום ההחזרה תלוי בנמל התעופה, ולכן חשוב לקרוא את הוראות האישור ולא להניח שמחזירים בדיוק בנקודת הקבלה. מוסרים מספר טיסה וטלפון זמין ומוודאים מראש את שעת המסירה וההחזרה.'),
   ('GPS בכל רכב', 'לפי התחייבות MM Cars, בכל רכב יש GPS. זהו מאפיין של השירות, ולא תוספת לבחירה בטופס. אם חשובה לכם שפת המערכת או צורת חיבור מסוימת לטלפון, כדאי לברר זאת לפני ההזמנה: GPS אינו מבטיח שכל מערכת תומכת בכל שפה או חיבור.'),
   ('דלק: מלא למלא', 'הרכב נמסר עם מיכל מלא ומוחזר עם מיכל מלא. בודקים את המפלס בקבלה ומתעדים כל אי-התאמה. לפני ההחזרה מתדלקים בדלק המתאים ושומרים קבלה. כך אפשר למנוע אי-הבנות בנוגע לתדלוק.'),
   ('קבלה והחזרה מחוץ לפולין', 'אפשר לבדוק מסירת רכב או איסופו במדינה אחרת, בכפוף לתיאום ואישור מראש. זו בקשה נפרדת מאישור לנסוע ברכב מפולין לחו״ל. המחיר, נקודת המפגש ותנאי התשלום נקבעים בהצעה; בקבלה בחו״ל יש להסדיר מראש את דרישת התשלום לפני המסירה.'),
   ('מה חשוב לבדוק בהצעה?', 'בודקים את מספר המקומות, נפח הכבודה, סוג תיבת ההילוכים, הפיקדון, תנאי כרטיס האשראי והוראות ההחזרה. אם דרוש כיסא לילד, מציינים מראש את גיל הילד ואת נתוני ההתאמה הנדרשים. ציוד נוסף ושירותים מיוחדים נחשבים מאושרים רק כשהם מופיעים בהצעה ובאישור.')]
 }
}

def navigation():
    return '<nav aria-label="חברות השכרה"><a href="rental-companies-review.html">השוואת החברות</a>' + ''.join(f'<a href="{LINKS[c["id"]]}">{c["name"]}</a>' for c in COMPANIES) + '</nav>'

def main():
    build()
    hub = OUT / 'rental-companies-review.html'
    text = hub.read_text(encoding='utf-8')
    for c in COMPANIES:
        marker = f"{c['fit']}</div></article>"
        assert marker in text
        text = text.replace(marker, f'{c["fit"]}</div><div class="actions"><a class="button secondary" href="{LINKS[c["id"]]}">מידע מעשי על {c["name"]} ←</a></div></article>')
    text = text.replace('</nav></div></header>', '</nav></div><div class="wrap" style="padding-bottom:14px;flex-wrap:wrap;min-height:0">'+navigation()+'</div></header>')
    hub.write_text(text, encoding='utf-8')
    for key, p in PROFILES.items():
        company = next(c for c in COMPANIES if c['id'] == key)
        logo = asset(f'wordpress/trip-rental-page/{key}.svg', 'image/svg+xml')
        facts = ''.join(f'<div class="standard"><h3>{a}</h3><p>{b}</p></div>' for a,b in p['facts'])
        sections = ''.join(f'<section class="explain"><h2>{a}</h2><p>{b}</p></section>' for a,b in p['sections'])
        page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{escape(p['title'])}</title><style>{STYLE}
        .profile{{max-width:950px}}.profile>section{{margin:22px 0}}.profile h1{{font-size:clamp(29px,4vw,43px)}}.profile h2{{font-size:23px}}.profile .standards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.profile .company-logo{{margin-top:26px;height:65px}}.profile .explain p{{max-width:790px}}.profile .explain{{padding:22px}}@media(max-width:600px){{.profile .standards{{grid-template-columns:1fr}}.site-head nav{{gap:12px}}}}
        </style></head><body><div class="review-bar" dir="ltr"><span><strong>ПРЕДОСМОТР ДЛЯ ОДОБРЕНИЯ</strong> · Сайт не изменён</span><a href="rental-companies-review.html">Общая статья</a></div>
        <header class="site-head"><div class="wrap"><a class="brand" href="rental-companies-review.html">Poland Rent a Car</a>{navigation()}</div></header>
        <main class="wrap profile"><img class="company-logo" src="{logo}" alt="{company['name']}"><h1>{p['title']}</h1><p class="lead">{p['lead']}</p><section class="standards">{facts}</section>{sections}
        <section class="personal-statement"><h2 style="color:white">הסטנדרט שלי — גם בהצעה של {company['name']}</h2><p>אני עידן, איש הקשר שלכם לפני ההזמנה ובמהלך ההשכרה. לקוחותיי מקבלים שירות במסגרת ההסכמות שלי עם החברה: יחס VIP, עדיפות בטיפול דרך אנשי הקשר שלי, ביטוח מלא עם ביטול השתתפות עצמית כולל גניבה, שמשות וגלגלים, וצמיגים מותאמים לעונה. הפיקדון ותנאי השחרור שלו מפורטים בהצעה; פיקדון וביטול השתתפות עצמית הם שני דברים שונים.</p></section>
        <section class="clarity"><h2>נוסעים לחו״ל? חשוב לדעת מה כלול</h2><p>בנסיעה לחו״ל שאושרה במסגרת החבילה שלי, הכיסוי כולל גם רכב חלופי מאותה קטגוריה והובלת הרכב שנפגע ממקום האירוע בחו״ל לפולין, ללא חיוב נוסף על השירותים האלה, בכפוף לתנאי ההשכרה, לאירוע מכוסה ולהוראות הדיווח. אם מתרחש אירוע, פונים מיד אליי ולמוקד לפי הוראות האישור ומתאמים את הטיפול לפני שמזמינים שירות עצמאית.</p><p>בהזמנה ישירה באתר חברת ההשכרה, אישור יציאה לחו״ל וכיסוי ביטוחי אינם מבטיחים כשלעצמם שהחלפה וגרירה לפולין כלולות. יש לבדוק את חבילת הסיוע שנרכשה בפועל.</p></section>
        <section class="explain"><h2>מה להכין לבקשת הצעה?</h2><p>תאריכים ושעות, עיר ונקודת קבלה והחזרה, מספר נוסעים ומזוודות, גיל הנהגים וותק הרישיון, מספר טיסה, צורך בכיסאות לילדים ותוכנית נסיעה למדינות אחרות. יש לבדוק מראש את דרישת הכרטיס על שם הנהג ואת תנאי הפיקדון. נהג צעיר או בעל ותק קצר חייבים לציין מראש כדי שאבדוק התאמה ועלות.</p></section>
        <section class="clarity"><h2>ביטוח רחב אינו כיסוי לכל מצב</h2><p>קנסות, לכלוך או נזק שאינו מכוסה בפנים הרכב, מעשה מכוון, שימוש שלא לפי הייעוד, נהיגה תחת השפעת אלכוהול או סמים והפרת תנאי ההשכרה אינם הופכים למכוסים בזכות ביטול ההשתתפות העצמית. התנאים והחריגים באישור ובחוזה קובעים. בכל ספק שואלים לפני ההזמנה.</p></section>
        <section class="cta"><div><h2>נבדוק אם זו החברה המתאימה לכם?</h2><p>תקבלו הצעה שמציגה את המחיר, הקבוצה, הפיקדון והשירותים שאושרו. מאחורי ההצעה יש אדם שמכיר את ההזמנה שלכם.</p></div><a class="button" href="https://poland-rent-car.com/request-form/">בקשת הצעה אישית</a></section><p><a href="rental-companies-review.html#comparison">← חזרה לטבלת ההשוואה בין ארבע החברות</a></p></main>
        <footer class="site-footer"><div class="wrap"><span>עידן · Poland Rent a Car</span><a href="mailto:idanrentacar@gmail.com">idanrentacar@gmail.com</a><a dir="ltr" href="https://wa.me/48533100636">+48 533 100 636 · WhatsApp</a></div></footer></body></html>'''
        (OUT / LINKS[key]).write_text(page, encoding='utf-8')
        print(OUT / LINKS[key])

if __name__ == '__main__':
    main()
