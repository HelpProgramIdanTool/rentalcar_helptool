import secrets
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from partners.models import PartnerAccess, PortalConfiguration


class Command(BaseCommand):
    help='Create a restricted, no-email test partner account. Password is shown only on first creation or explicit reset.'
    def add_arguments(self,parser):
        parser.add_argument('--username',default='idan-partner-test')
        parser.add_argument('--email',required=True)
        parser.add_argument('--reset-password',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:validate_email(options['email'])
        except ValidationError:raise CommandError('Invalid email')
        User=get_user_model()
        user,created=User.objects.get_or_create(username=options['username'])
        if not created and not PartnerAccess.objects.filter(user=user,is_test=True).exists():
            raise CommandError('Existing account is not a test partner; nothing changed.')
        if user.is_staff or user.is_superuser:raise CommandError('Refusing to use an operator account.')
        password=None
        if created or options['reset_password']:
            password=secrets.token_urlsafe(18)
            user.set_password(password)
        user.email=options['email'];user.is_active=True;user.save()
        PartnerAccess.objects.update_or_create(user=user,defaults={'display_name':'חשבון הבדיקה של עידן',
            'email':options['email'],'is_test':True,'is_active':True})
        config=PortalConfiguration.objects.first()
        if config:
            config.workspace_copy_email=options['email']
            config.save(update_fields=['workspace_copy_email'])
        self.stdout.write('URL: https://rentalcar-helptool.onrender.com/partners/workspace/')
        self.stdout.write('USERNAME: '+user.username)
        if password:self.stdout.write('PASSWORD: '+password)
        else:self.stdout.write('Existing password unchanged. Use --reset-password only if needed.')
        self.stdout.write('TEST MODE: persistent server data; no supplier emails or actual bookings.')
