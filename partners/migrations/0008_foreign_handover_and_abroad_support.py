"""Owner-confirmed offer facts, 21 November 2026. No prices or bookings changed."""
from django.db import migrations

FACTS={
    'kaizenrent':{'foreign_handover':'לא - קבלה והחזרה בפולין בלבד','gps_included':'לפי מפרט הרכב'},
    'carfree':{'foreign_handover':'אפשרי - בתיאום ואישור מראש','gps_included':'לפי מפרט הרכב'},
    'onerent':{'foreign_handover':'אפשרי - בתיאום ואישור מראש','gps_included':'לפי מפרט הרכב'},
    'mmcars':{'foreign_handover':'אפשרי - בתיאום ואישור מראש','gps_included':'כן - GPS בכל רכב','gps':'כלול בכל רכב'},
    'mmcarsrental':{'foreign_handover':'אפשרי - בתיאום ואישור מראש','gps_included':'כן - GPS בכל רכב','gps':'כלול בכל רכב'},
}
CONTENT={
    'foreign_handover_label':'קבלה או החזרה מחוץ לפולין',
    'gps_included_label':'מערכת ניווט GPS ברכב',
    'foreign_collection_note':'קבלה והחזרה מחוץ לפולין שונות מנסיעה לחו״ל. ב-Kaizen מקבלים ומחזירים בפולין בלבד; אפשר לצאת מפולין עם הרכב באישור מראש.',
    'abroad_support':{
        'title':'ללקוחות עידן: גם רכב חלופי וגרירה מחו״ל לפולין',
        'body':'כאשר היציאה לחו״ל אושרה ונכללה בהצעה דרך עידן, במקרה מכוסה שמשבית את הרכב גם מחוץ לפולין כלולים רכב חלופי מאותה קטגוריה וגרירת הרכב הפגוע ממקום האירוע לפולין, ללא תשלום נוסף על שירותים אלה. יש לדווח ולקבל הנחיות לפי תנאי ההשכרה.',
        'direct_booking_note':'אישור יציאה וכיסוי ביטוחי בהזמנה ישירה באתר החברה אינם מבטיחים כשלעצמם רכב חלופי או גרירה לפולין; בחלק מהמסלולים נדרשת חבילה נוספת.',
    },
}

def seed(apps,schema_editor):
    Summary=apps.get_model('partners','SupplierSummary')
    Config=apps.get_model('partners','PortalConfiguration')
    for summary in Summary.objects.all():
        key=''.join(summary.name.casefold().split())
        if key in FACTS:
            summary.facts={**summary.facts,**FACTS[key]}
            summary.save(update_fields=['facts'])
    for config in Config.objects.all():
        config.content={**config.content,**CONTENT}
        config.save(update_fields=['content'])

class Migration(migrations.Migration):
    dependencies=[('partners','0007_workspace_live_links')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
