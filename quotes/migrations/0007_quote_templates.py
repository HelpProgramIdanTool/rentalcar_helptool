from django.db import migrations, models
import django.db.models.deletion


BLOCKS = [
    (10, "GREETING", "", "שלום רב,\nתודה שפניתם אלינו. הכנתי עבורכם הצעות מחיר בהתאם לפרטי הבקשה שמסרתם. אנא קראו את ההצעה עד סופה; היא כוללת מידע חשוב ואת רשימת הפרטים הדרושים לביצוע הזמנה.", ""),
    (20, "IMPORTANT", "חשוב לדעת", "• ההצעה מחושבת לפי גיל הנהגים שנמסר. נהג צעיר עשוי להיות מחויב בתוספת בהתאם לכללי החברה.\n• חברת ההשכרה מתחייבת לקבוצת רכב ולא לדגם מסוים. הדגמים המופיעים הם דוגמאות.\n• המחיר והזמינות תקפים למועד הכנת ההצעה ועשויים להשתנות עד לאישור ההזמנה בוואוצ'ר רשמי.", ""),
    (30, "CROSS_BORDER", "יציאה מגבולות פולין", "יציאה מפולין מחייבת אישור מראש והרחבת כיסוי מתאימה. האישור, המדינות המותרות והמחיר משתנים בין החברות. תשלומי כבישי אגרה במדינות אחרות אינם כלולים במחיר ההשכרה.", "CROSS_BORDER"),
    (40, "PAYMENT_DEPOSIT", "תשלום ופיקדון", "אופן התשלום, גובה הפיקדון ותנאי החסימה בכרטיס האשראי מפורטים בכל אפשרות בהתאם לחברת ההשכרה. אין להסתמך על סכום פיקדון אחיד לכל החברות או לכל קבוצות הרכב.", ""),
    (50, "BOOKING_PROCESS", "תהליך ההזמנה", "לאחר שתבחרו אפשרות, שלחו אליי את הפרטים המופיעים בסוף ההצעה. הבקשה תועבר לחברת ההשכרה. רכב נחשב מובטח רק לאחר שהחברה מאשרת את ההזמנה ומנפיקה וואוצ'ר רשמי עם מספר הזמנה.", ""),
    (60, "CHANGES_CANCELLATION", "שינויים וביטולים", "יש להודיע על שינוי או ביטול מוקדם ככל האפשר. התנאים המדויקים נקבעים לפי החברה וההזמנה. מומלץ לרכז שינויים ולשלוח עדכון אחד מסודר לפני הנסיעה.", ""),
    (70, "DURING_RENTAL", "במהלך ההשכרה", "במהלך השהייה יש לפנות תחילה לשירות הלקוחות של חברת ההשכרה שמסרה את הרכב. פרטי הקשר והוראות האיסוף וההחזרה יופיעו בוואוצ'ר.", ""),
    (80, "ORDER_DETAILS", "כדי לבצע הזמנה", "נא לשלוח:\n• האפשרות וקבוצת הרכב שבחרתם;\n• שמות הנהגים באנגלית כפי שמופיעים ברישיון;\n• מספר טלפון זמין בפולין;\n• מספר טיסה במקרה של איסוף בשדה התעופה;\n• שם וכתובת המלון במקרה של מסירה למלון;\n• כתובת מגורים מלאה ומיקוד באנגלית;\n• גיל ומשקל הילד כאשר נדרש מושב בטיחות.", ""),
    (90, "SIGNATURE", "", "לשאלות ניתן לפנות אליי במייל או בטלפון/WhatsApp.\n\nבכבוד רב,\nעידן רץ", ""),
]


def seed_hebrew_template(apps, schema_editor):
    Template = apps.get_model("quotes", "QuoteTemplate")
    Block = apps.get_model("quotes", "QuoteTemplateBlock")
    template, _ = Template.objects.get_or_create(name="Standard customer offer", language="Hebrew", defaults={"is_active": True})
    for order, key, title, content, condition in BLOCKS:
        Block.objects.get_or_create(template=template, block_key=key, defaults={"title": title, "content": content, "display_order": order, "condition_code": condition})


class Migration(migrations.Migration):
    dependencies = [("quotes", "0006_quote_option")]
    operations = [
        migrations.CreateModel(name="QuoteTemplate", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=120)), ("language", models.CharField(max_length=30)), ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True))], options={"ordering": ["language", "name"]}),
        migrations.CreateModel(name="QuoteTemplateBlock", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("block_key", models.CharField(max_length=50)), ("title", models.CharField(blank=True, max_length=150)), ("content", models.TextField()), ("display_order", models.PositiveSmallIntegerField(default=0)), ("condition_code", models.CharField(blank=True, max_length=40)), ("is_active", models.BooleanField(default=True)), ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks", to="quotes.quotetemplate"))], options={"ordering": ["display_order", "id"]}),
        migrations.CreateModel(name="QuoteDocumentBlock", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("block_key", models.CharField(max_length=50)), ("title", models.CharField(blank=True, max_length=150)), ("content", models.TextField()), ("display_order", models.PositiveSmallIntegerField(default=0)), ("condition_code", models.CharField(blank=True, max_length=40)), ("is_enabled", models.BooleanField(default=True)), ("quote", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="document_blocks", to="quotes.quote")), ("source_block", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="quotes.quotetemplateblock"))], options={"ordering": ["display_order", "id"]}),
        migrations.AddConstraint(model_name="quotetemplateblock", constraint=models.UniqueConstraint(fields=("template", "block_key"), name="unique_block_key_per_template")),
        migrations.AddConstraint(model_name="quotedocumentblock", constraint=models.UniqueConstraint(fields=("quote", "block_key"), name="unique_document_block_per_quote")),
        migrations.RunPython(seed_hebrew_template, migrations.RunPython.noop),
    ]
