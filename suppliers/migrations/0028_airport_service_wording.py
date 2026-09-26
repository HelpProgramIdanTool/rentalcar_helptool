from django.db import migrations, models


WORDING = {
    "DESK": (
        "קבלת הרכב בדלפק חברת ההשכרה בשדה התעופה.",
        "Vehicle collection is at the rental company's airport desk.",
    ),
    "MEET": (
        "נציג חברת ההשכרה יפגוש אתכם בשדה התעופה ויכוון אתכם לקבלת הרכב.",
        "A rental company representative will meet you at the airport.",
    ),
    "UNKNOWN": (
        "מקום קבלת הרכב יתואם לפני ביצוע ההזמנה.",
        "The exact airport collection procedure will be confirmed with the booking.",
    ),
    "RETURN_DESK": (
        "החזרת הרכב מתבצעת בעמדת חברת ההשכרה בשדה התעופה.",
        "Vehicle return is at the rental company's airport location.",
    ),
    "RETURN_MEET": (
        "נציג חברת ההשכרה יתאם אתכם את מקום ואופן החזרת הרכב בשדה התעופה.",
        "A rental company representative will coordinate the airport return with you.",
    ),
    "RETURN_UNKNOWN": (
        "מקום ואופן החזרת הרכב בשדה התעופה יאושרו בעת ביצוע ההזמנה.",
        "The exact airport return procedure will be confirmed with the booking.",
    ),
}


def configure_wording(apps, schema_editor):
    Wording = apps.get_model("suppliers", "AirportPickupWording")
    for code, (text_he, text_en) in WORDING.items():
        Wording.objects.update_or_create(
            method_code=code,
            defaults={"text_he": text_he, "text_en": text_en},
        )


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0027_supplier_charge_after_hours_at_airports")]

    operations = [
        migrations.AddField(
            model_name="airportpickupwording",
            name="text_en",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.RunPython(configure_wording, migrations.RunPython.noop),
    ]
