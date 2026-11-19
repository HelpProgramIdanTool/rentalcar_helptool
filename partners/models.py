import uuid
from django.conf import settings
from django.db import models


class PartnerAccess(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='partner_access')
    display_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=60, blank=True)
    is_test = models.BooleanField(default=False, help_text='Тестовый кабинет: письма и реальные бронирования запрещены.')
    pricing_sub_agent = models.ForeignKey('employees.SubAgent', null=True, blank=True, on_delete=models.PROTECT,
        help_text='Выбрать только если в ручной оферте этому партнёру уже применяется такой режим цен. Пусто — обычные цены.')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name


class PortalConfiguration(models.Model):
    owner_email = models.EmailField(blank=True)
    workspace_copy_email = models.EmailField(blank=True)
    email_language = models.CharField(max_length=30, default='Hebrew', choices=[('Hebrew','עברית')])
    content = models.JSONField(default=dict)

    def __str__(self):
        return 'Настройки кабинета партнёров'


class SupplierSummary(models.Model):
    supplier = models.OneToOneField('suppliers.Supplier', null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=120, unique=True)
    facts = models.JSONField(default=dict)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'pk']

    def __str__(self):
        return self.name


class PartnerDraft(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(PartnerAccess, on_delete=models.PROTECT, related_name='drafts')
    trip = models.JSONField(default=dict)
    selected_groups = models.JSONField(default=list)
    quote = models.OneToOneField('quotes.Quote', null=True, blank=True, on_delete=models.PROTECT)
    manual_message = models.TextField(blank=True)
    manual_requested = models.BooleanField(default=False)
    delivery_html = models.TextField(blank=True)
    delivery_text = models.TextField(blank=True)
    delivery_subject = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PartnerDelivery(models.Model):
    draft = models.ForeignKey(PartnerDraft, on_delete=models.PROTECT, related_name='deliveries')
    recipient = models.EmailField()
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['draft', 'recipient'], name='unique_partner_delivery')]


class PartnerLoginAttempt(models.Model):
    username_key = models.CharField(max_length=64, db_index=True)
    ip_key = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class PartnerWorkspaceRecord(models.Model):
    """Persisted workspace test data, isolated from actual bookings and statistics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(PartnerAccess, on_delete=models.PROTECT, related_name='workspace_records')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='orders')
    kind = models.CharField(max_length=12, choices=[('QUOTE','Оферта'),('ORDER','Тестовый заказ'),('MANUAL','Ручной запрос'),('CHANGE','Изменение / отмена')])
    status = models.CharField(max_length=20, default='DRAFT')
    customer_name = models.CharField(max_length=200, blank=True)
    trip = models.JSONField(default=dict)
    options = models.JSONField(default=list)
    price_versions = models.JSONField(default=dict)
    details = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    is_test = models.BooleanField(default=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def number(self):
        return 'TEST-'+self.kind+'-'+self.pk.hex[:8].upper()
