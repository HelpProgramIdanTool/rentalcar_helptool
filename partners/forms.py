from datetime import datetime, time
from zoneinfo import ZoneInfo
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from suppliers.models import OfferCity
from quotes.forms import FirstInquiryForm
from .models import PartnerAccess, PortalConfiguration


def portal_date_field(label):
    return forms.DateField(label=label, input_formats=['%d.%m.%Y', '%Y-%m-%d'],
        widget=forms.DateInput(format='%d.%m.%Y', attrs={
            'placeholder':'DD.MM.YYYY', 'inputmode':'numeric', 'dir':'ltr',
            'maxlength':'10', 'pattern':r'[0-9]{2}\.[0-9]{2}\.[0-9]{4}',
            'data-portal-date':'true'}))


class PartnerLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not PartnerAccess.objects.filter(user=user, is_active=True).exists():
            raise forms.ValidationError('פרטי הכניסה אינם תקינים.')


class TripForm(forms.Form):
    driver_ok = forms.BooleanField(initial=True, required=False, label='כל הנהגים מעל גיל 24 ועם רישיון מעל שנה')
    credit_ok = forms.BooleanField(initial=True, required=False, label='כרטיס האשראי על שם הנהג הראשי')
    border_ok = forms.BooleanField(initial=True, required=False, label='ידוע לי שחובה לציין יציאה למדינות אחרות')
    pickup_date = portal_date_field('תאריך קבלה')
    pickup_time = forms.ChoiceField(choices=FirstInquiryForm.TIME_CHOICES, initial='10:00', label='שעת קבלה')
    pickup_city = forms.ChoiceField(label='עיר קבלה')
    pickup_service = forms.ChoiceField(choices=[('AIRPORT','נמל תעופה'),('CITY_BRANCH','סניף בעיר'),('ADDRESS','מלון / כתובת')], label='מקום קבלה')
    pickup_address = forms.CharField(max_length=300, required=False, label='שם המלון וכתובת לקבלה')
    return_date = portal_date_field('תאריך החזרה')
    return_time = forms.ChoiceField(choices=FirstInquiryForm.TIME_CHOICES, initial='10:00', label='שעת החזרה')
    return_city = forms.ChoiceField(label='עיר החזרה')
    return_service = forms.ChoiceField(choices=[('AIRPORT','נמל תעופה'),('CITY_BRANCH','סניף בעיר'),('ADDRESS','מלון / כתובת')], label='מקום החזרה')
    return_address = forms.CharField(max_length=300, required=False, label='שם המלון וכתובת להחזרה')
    cross_border = forms.BooleanField(required=False, label='נסיעה למדינות אחרות')
    countries = forms.CharField(required=False, max_length=300, label='מדינות נוספות בנסיעה')
    drivers = forms.IntegerField(min_value=1, max_value=9, initial=1, label='מספר נהגים')
    seats = forms.IntegerField(min_value=0, max_value=9, initial=0, label='כיסאות ילדים / בוסטרים')
    gps = forms.BooleanField(required=False, label='ניווט GPS')
    chains = forms.BooleanField(required=False, label='שרשראות שלג')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = PortalConfiguration.objects.first()
        for key, label in (config.content.get('declarations', {}) if config else {}).items():
            if key in self.fields:
                self.fields[key].label = label
        # No free-text foreign city: nonstandard routes go to Idan.
        self.cities = {c.name:c for c in OfferCity.objects.filter(is_active=True)}
        choices = [('', 'בחרו עיר'), *[(c.name, c.label) for c in self.cities.values()]]
        for side in ('pickup', 'return'):
            self.fields[side+'_city'].choices = choices
        for field in self.fields.values():
            field.error_messages.update(required='נא למלא שדה זה.', invalid='נא לבדוק את הערך שהוזן.', invalid_choice='נא לבחור אפשרות מהרשימה.')

    def clean(self):
        data = super().clean()
        zone = ZoneInfo('Europe/Warsaw')
        for side in ('pickup', 'return'):
            date, clock = data.get(side+'_date'), data.get(side+'_time')
            if date and clock:
                wall = datetime.combine(date, time.fromisoformat(clock))
                value = wall.replace(tzinfo=zone, fold=0)
                if value.astimezone(ZoneInfo('UTC')).astimezone(zone).replace(tzinfo=None) != wall:
                    self.add_error(side+'_time', 'השעה אינה קיימת ביום המעבר לשעון קיץ.')
                data[side+'_datetime'] = value
            if data.get(side+'_service') == 'ADDRESS' and not data.get(side+'_address'):
                self.add_error(side+'_address', 'נא לציין שם מלון וכתובת מלאה.')
        start, end = data.get('pickup_datetime'), data.get('return_datetime')
        if start and start <= timezone.now():
            self.add_error('pickup_date', 'מועד הקבלה כבר עבר.')
        if start and end and end <= start:
            self.add_error('return_date', 'ההחזרה חייבת להיות אחרי הקבלה.')
        foreign = any(self.cities[data[side+'_city']].cross_border_required for side in ('pickup','return') if data.get(side+'_city') in self.cities)
        data['foreign_route'] = foreign
        if foreign:
            data['cross_border'] = True
        if data.get('cross_border') and not data.get('countries'):
            self.add_error('countries', 'נא לציין את המדינות הנוספות, כולל מדינת קבלה או החזרה מחוץ לפולין.')
        return data


class RecipientForm(forms.Form):
    customer_name = forms.CharField(max_length=100, label='שם הלקוח שעבורו ההצעה')
    partner_email = forms.EmailField(label='שליחת ההצעה אליי')
    customer_email = forms.EmailField(required=False, label='דואר אלקטרוני של הלקוח — לא חובה')
    send_customer = forms.BooleanField(required=False, label='לשלוח עותק גם ללקוח')
    checked = forms.BooleanField(label='בדקתי את הנתונים ואת תנאי ההצהרה עבור הנסיעה הזאת')

    def clean(self):
        data = super().clean()
        if data.get('send_customer') and not data.get('customer_email'):
            self.add_error('customer_email', 'נא למלא כתובת לפני שליחה ללקוח.')
        return data
