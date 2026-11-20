import secrets
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from partners.models import PartnerAccess, PortalConfiguration

class Command(BaseCommand):
    help='Create a partner-only login; password is printed once, never emailed.'
    def add_arguments(self,parser):
        parser.add_argument('--email',required=True)
        parser.add_argument('--name',required=True)
        parser.add_argument('--username')
        parser.add_argument('--phone',default='')
        parser.add_argument('--test',action='store_true')
        parser.add_argument('--reset-password',action='store_true')
        parser.add_argument('--owner-copy')
    @transaction.atomic
    def handle(self,*args,**options):
        try:
            validate_email(options['email'])
            if options['owner_copy']:validate_email(options['owner_copy'])
        except ValidationError:raise CommandError('Invalid email')
        username=options['username'] or options['email'].strip().lower()
        user,created=get_user_model().objects.get_or_create(username=username)
        access=PartnerAccess.objects.filter(user=user).first()
        if user.is_staff or user.is_superuser or (not created and not access):
            raise CommandError('Existing login is not a partner account; nothing changed.')
        if access and access.is_test!=options['test']:
            raise CommandError('Refusing to change the mode of an existing account.')
        password=None
        if created or options['reset_password']:
            password=secrets.token_urlsafe(18);user.set_password(password)
        user.email=options['email'];user.is_active=True;user.save()
        PartnerAccess.objects.update_or_create(user=user,defaults={
            'display_name':options['name'],'email':options['email'],'phone':options['phone'],
            'is_test':options['test'],'is_active':True})
        if options['owner_copy']:
            config=PortalConfiguration.objects.first() or PortalConfiguration.objects.create()
            config.workspace_copy_email=options['owner_copy'];config.owner_email=options['owner_copy']
            config.save(update_fields=['workspace_copy_email','owner_email'])
        self.stdout.write('URL: https://rentalcar-helptool.onrender.com/partners/login/')
        self.stdout.write('USERNAME: '+username)
        self.stdout.write('MODE: '+('TEST' if options['test'] else 'LIVE'))
        self.stdout.write('PASSWORD: '+password if password else 'Existing password unchanged.')
