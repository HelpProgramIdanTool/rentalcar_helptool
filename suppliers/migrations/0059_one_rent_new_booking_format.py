from django.db import migrations


TEMPLATE = '''Customer: $driver_names

Address: $address
Phone: $phone
Email: $email

Rental Details

Pick-up Date: $pickup_date
Pick-up Location: $pickup_location
Flight Number: $flight_number

Return Date: $return_date
Return Location: $return_location

Vehicle Class: $vehicle_class
Days: $days

Additional Services

$services

Deposit: $deposit
Price calculation: $price_calculation'''

OPTIONS = {
    'included_services':['Full Vehicle Protection VIP'],
    'airport_service_label':'Airport Vehicle Delivery',
    'skip_service_codes':['AIRPORT_FEE','CITY_AIRPORT_DELIVERY','ADDITIONAL_DRIVER'],
    'city_names':{'Warszawa':'Warsaw'},
    'service_names':{
        'CHILD_SEAT':'Child Seat – Group',
        'CROSS_BORDER':'Access to Travel Abroad',
        'EXTRA_CLEANING':'Extra Cleaning',
        'GPS':'GPS Navigation',
        'SNOW_CHAINS':'Snow Chains',
        'OUTSIDE_CITY_DELIVERY':'Delivery / Return Outside the City',
    },
}


def enable(apps,schema_editor):
    Supplier = apps.get_model('suppliers','Supplier')
    Supplier.objects.using(schema_editor.connection.alias).filter(
        supplier_name__iexact='One Rent',new_booking_email_template='').update(
            new_booking_email_template=TEMPLATE,new_booking_email_options=OPTIONS)


class Migration(migrations.Migration):
    dependencies = [('suppliers','0058_supplier_new_booking_email_options_and_more')]
    operations = [migrations.RunPython(enable,migrations.RunPython.noop)]
