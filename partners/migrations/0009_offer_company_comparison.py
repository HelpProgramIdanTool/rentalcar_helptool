"""Editable translations for the existing company comparison facts."""
from django.db import migrations

KEYS = ['age', 'pickup', 'return', 'fuel', 'gps_included', 'foreign_handover']
CONFIG = {
 'Hebrew': dict(title='השוואה קצרה בין החברות בהצעה',
   columns=['חברה','גיל הרכב','קבלה','החזרה','דלק','GPS ברכב','מסירה מחוץ לפולין'],
   unknown='לבדיקה בהצעה', link_label='מידע נוסף על החברות ותנאי השירות',
   url='https://poland-rent-car.com/rental-companies/',
   common='בכל האפשרויות: ביטוח עם ביטול השתתפות עצמית כולל גניבה, שמשות וגלגלים, צמיגים לעונה וליווי אישי של עידן. בנסיעה מאושרת לחו״ל במסגרת החבילה: רכב חלופי מאותה קטגוריה וגרירת הרכב שנפגע לפולין, בכפוף לתנאי הכיסוי והדיווח.',
   note='ההשוואה כללית. המחיר, הפיקדון, השירותים והוראות המסירה נקבעים בהצעה ובאישור. מסירה בחו״ל שונה מאישור נסיעה לחו״ל.'),
 'English': dict(title='Compare the companies in this offer',
   columns=['Company','Vehicle age','Collection','Return','Fuel','Onboard GPS','Handover outside Poland'],
   unknown='Check your offer',link_label='More about the companies and service conditions',
   url='https://poland-rent-car.com/english/compare-rental-companies/',
   common='All options: insurance with zero excess including theft, glass and wheels, seasonal tyres and personal support from Idan. Approved cross-border travel under the package includes a replacement in the same category and transport of the damaged car to Poland, subject to coverage and reporting conditions.',
   note='General comparison. The quotation and confirmation define the price, deposit, services and handover instructions. Foreign handover is different from permission to drive abroad.'),
 'Polish': dict(title='Porównanie firm w tej ofercie',
   columns=['Firma','Wiek auta','Odbiór','Zwrot','Paliwo','GPS w aucie','Wydanie poza Polską'],
   unknown='Sprawdź w ofercie',link_label='Więcej o firmach i warunkach obsługi (po angielsku)',
   url='https://poland-rent-car.com/english/compare-rental-companies/',
   common='Wszystkie opcje: ubezpieczenie ze zniesionym udziałem własnym obejmujące kradzież, szyby i koła, opony sezonowe i osobista pomoc Idana. Zatwierdzony wyjazd zagraniczny w ramach pakietu obejmuje auto zastępcze tej samej kategorii i transport uszkodzonego auta do Polski, zgodnie z warunkami ochrony i zgłoszenia.',
   note='Porównanie ogólne. Cena, kaucja, usługi i instrukcje wydania wynikają z oferty i potwierdzenia. Wydanie za granicą różni się od zgody na wyjazd zagraniczny.'),
 'Russian': dict(title='Сравнение фирм в этой оферте',
   columns=['Фирма','Возраст авто','Получение','Возврат','Топливо','GPS в машине','Выдача вне Польши'],
   unknown='Уточнить в оферте',link_label='Подробнее о фирмах и условиях (на английском)',
   url='https://poland-rent-car.com/english/compare-rental-companies/',
   common='Во всех вариантах: страховка с отменой личного участия, включая кражу, стекла и колёса, сезонные шины и личная поддержка Идана. Одобренный выезд за границу в рамках пакета включает замену машиной той же категории и перевозку повреждённой машины в Польшу по условиям покрытия и уведомления.',
   note='Общее сравнение. Цена, депозит, услуги и место передачи определяются офертой и подтверждением. Получение за границей отличается от разрешения выехать за границу.'),
}

def seed(apps, schema_editor):
    Config = apps.get_model('partners', 'PortalConfiguration')
    Summary = apps.get_model('partners', 'SupplierSummary')
    for config in Config.objects.all():
        existing = config.content.get('offer_comparison', {})
        config.content = {**config.content, 'offer_comparison': {
            **{lang: {**values, 'keys': KEYS} for lang, values in CONFIG.items()}, **existing}}
        config.save(update_fields=['content'])
    for summary in Summary.objects.all():
        facts = summary.facts
        # Translate existing values; no prices or supplier calculation codes.
        dictionaries = {
          'English': {'לא צוין':'Not specified','עד שנתיים ✓':'Up to 2 years',
            'בטרמינל':'Terminal','תמיד בטרמינל':'Terminal', 'תלוי בנמל התעופה':'Depends on airport',
            'מלא → מלא':'Full to full','אותה כמות שקיבלתם':'Same level as received',
            'לפי מפרט הרכב':'Check vehicle specification','כן - GPS בכל רכב':'GPS in every car',
            'לא - קבלה והחזרה בפולין בלבד':'Poland only','אפשרי - בתיאום ואישור מראש':'By prior agreement'},
          'Polish': {'לא צוין':'Nie określono','עד שנתיים ✓':'Do 2 lat',
            'בטרמינל':'Terminal','תמיד בטרמינל':'Terminal','תלוי בנמל התעופה':'Zależnie od lotniska',
            'מלא → מלא':'Pełny do pełnego','אותה כמות שקיבלתם':'Ten sam poziom paliwa',
            'לפי מפרט הרכב':'Według specyfikacji auta','כן - GPS בכל רכב':'GPS w każdym aucie',
            'לא - קבלה והחזרה בפולין בלבד':'Tylko Polska','אפשרי - בתיאום ואישור מראש':'Po wcześniejszym uzgodnieniu'},
          'Russian': {'לא צוין':'Не указан','עד שנתיים ✓':'До 2 лет',
            'בטרמינל':'Терминал','תמיד בטרמינל':'Терминал','תלוי בנמל התעופה':'Зависит от аэропорта',
            'מלא → מלא':'Полный → полный','אותה כמות שקיבלתם':'С тем же уровнем топлива',
            'לפי מפרט הרכב':'По комплектации','כן - GPS בכל רכב':'GPS в каждой машине',
            'לא - קבלה והחזרה בפולין בלבד':'Только Польша','אפשרי - בתיאום ואישור מראש':'По согласованию'},
        }
        translations = dict(facts.get('translations', {}))
        for lang, dictionary in dictionaries.items():
            translated = {key: dictionary[facts[key]] for key in KEYS if facts.get(key) in dictionary}
            translations[lang] = {**translated, **translations.get(lang, {})}
        summary.facts = {**facts, 'translations': translations}
        summary.save(update_fields=['facts'])

class Migration(migrations.Migration):
    dependencies = [('partners', '0008_foreign_handover_and_abroad_support')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
