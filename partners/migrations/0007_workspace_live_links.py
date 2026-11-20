from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('partners','0006_test_workspace'),('bookings','0025_booking_pickup_country_booking_return_country')]
    operations = [
        migrations.AlterField(model_name='partnerworkspacerecord',name='kind',field=models.CharField(max_length=12,choices=[('QUOTE','Оферта'),('ORDER','Заказ'),('MANUAL','Ручной запрос'),('CHANGE','Изменение / отмена')])),
        migrations.AddField(model_name='partnerworkspacerecord',name='draft',field=models.OneToOneField(null=True,blank=True,on_delete=django.db.models.deletion.PROTECT,related_name='workspace_record',to='partners.partnerdraft')),
        migrations.AddField(model_name='partnerworkspacerecord',name='booking',field=models.OneToOneField(null=True,blank=True,on_delete=django.db.models.deletion.PROTECT,related_name='partner_workspace_record',to='bookings.booking')),
    ]
