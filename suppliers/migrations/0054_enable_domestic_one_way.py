from django.db import migrations


def configure_one_way(apps, schema_editor):
    Supplier=apps.get_model('suppliers','Supplier')
    Extra=apps.get_model('suppliers','SupplierExtra')
    alias=schema_editor.connection.alias
    for supplier in Supplier.objects.using(alias).filter(supplier_name__iexact='Car Free'):
        extra,_=Extra.objects.using(alias).get_or_create(supplier_id=supplier.pk,extra_code='ONE_WAY_PL',defaults={
            'name':'One-way rental in Poland','category':'DELIVERY',
            'description':'Owner confirmed 14.11.2026: different Polish cities only. Day bands and amounts come from the supplier tariff.'})
        Extra.objects.using(alias).filter(pk=extra.pk).update(automatic_rule='DOMESTIC_ONE_WAY',
            customer_name_he='החזרת הרכב בעיר אחרת בפולין',is_active=True)
        # Never invent or overwrite supplier prices. Missing rates block a full
        # calculation until the operator imports the confirmed tariff.


class Migration(migrations.Migration):
    dependencies=[('suppliers','0053_supplierextra_customer_name_he')]
    operations=[migrations.RunPython(configure_one_way,migrations.RunPython.noop)]
