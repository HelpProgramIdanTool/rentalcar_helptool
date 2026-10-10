from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from decimal import Decimal
from .models import Reconciliation, Row, Revision, Upload
from .forms import UploadForm, PaymentForm, CalculationForm
from .parsing import read_rows
from . import services
from bookings.models import Booking


@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    list_display = ['month','supplier','state','invoice_number','incoming','worker','workspace']
    list_filter = ['month','state','supplier']
    fields = ['month','supplier','employee','rate','vat']
    actions = ['download_selected']

    def save_model(self, request, obj, form, change):
        if not change:
            previous = Reconciliation.objects.filter(supplier=obj.supplier).exclude(direct_orderer='').order_by('-month').first()
            if previous:
                obj.direct_orderer = previous.direct_orderer
                obj.direct_prefixes = previous.direct_prefixes
                obj.direct_rate = previous.direct_rate
        super().save_model(request,obj,form,change)

    @admin.action(description='Скачать общий Excel выбранных сверок')
    def download_selected(self, request, queryset):
        selected = list(queryset)
        if len({obj.month for obj in selected}) != 1:
            self.message_user(request, 'Выберите сверки одного месяца.', level=messages.ERROR)
            return
        summary, rows = {}, []
        net = commission = Decimal(0)
        for batch in selected:
            calculation = services.totals(batch)
            net += calculation['net']; commission += calculation['commission']
            summary[str(batch.supplier)] = f"{batch.get_state_display()} | Employee net {calculation['net']} | Employee commission {calculation['commission']} | My direct commission {calculation['direct_commission']} | Invoice {batch.invoice_number} | Received {batch.received} | Employee paid {batch.employee_paid}"
            version = batch.revisions.first()
            if version:
                for row in version.snapshot['rows']:
                    rows.append(dict(row, note=f'{batch.supplier}: ' + row['note']))
        summary['Total employee net'] = str(net)
        summary['Total employee commission'] = str(commission)
        content = services.workbook({'summary':summary, 'rows':rows})
        response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="monthly_reconciliation_{selected[0].month:%Y-%m}.xlsx"'
        response['Cache-Control'] = 'private, no-store'
        return response

    def get_readonly_fields(self, request, obj=None):
        return self.fields if obj else []

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Оплачено мне')
    def incoming(self, obj):
        if obj.invoice_amount is None:
            return 'Фактура не внесена'
        return 'Оплачено' if obj.received >= obj.invoice_amount else f'{obj.received} / {obj.invoice_amount}'

    @admin.display(description='Оплачено работнику')
    def worker(self, obj):
        return f'{obj.employee_paid} / {services.totals(obj)["commission"]}'

    @admin.display(description='Действия')
    def workspace(self, obj):
        return format_html('<a href="{}">Открыть сверку</a>', reverse('admin:reconciliation_workspace', args=[obj.pk]))

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('admin:reconciliation_workspace', obj.pk)

    def get_urls(self):
        return [path('<int:pk>/workspace/', self.admin_site.admin_view(self.work), name='reconciliation_workspace'),
                path('<int:pk>/excel/', self.admin_site.admin_view(self.excel), name='reconciliation_excel')] + super().get_urls()

    def checked(self, request, pk):
        if not self.has_view_permission(request) or (request.method=='POST' and not self.has_change_permission(request)):
            raise PermissionDenied
        return get_object_or_404(Reconciliation, pk=pk)

    def excel(self, request, pk):
        batch = self.checked(request, pk)
        version = request.GET.get('version')
        revision = get_object_or_404(Revision, pk=version, reconciliation=batch) if version else batch.revisions.first()
        own = request.GET.get('own')=='1'
        if own and (not revision or not revision.own_excel):
            self.message_user(request,'Сначала загрузите свои записи со столбцом номера заказа.',level=messages.WARNING)
            return redirect('admin:reconciliation_workspace',pk)
        content = bytes(revision.own_excel if own else revision.excel) if revision else services.workbook({'summary':{'State':'DRAFT'},'rows':[]})
        response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{"own_orders" if own else "reconciliation"}_{batch.month:%Y-%m}_{batch.supplier_id}_v{revision.pk if revision else 0}.xlsx"'
        response['Cache-Control'] = 'private, no-store'
        return response

    def work(self, request, pk):
        batch = self.checked(request, pk)
        kind = request.GET.get('upload_kind','OWN')
        if kind not in ('OWN','SUPPLIER','EMPLOYEE'):
            kind = 'OWN'
        previous = Upload.objects.filter(reconciliation__supplier=batch.supplier, kind=kind).order_by('-pk').first()
        initial = {'kind':kind}
        if previous and 'number' in previous.mapping:
            initial.update(previous.mapping)
            initial['return_column'] = initial.pop('return','')
        upload = UploadForm(initial=initial)
        payment = PaymentForm(instance=batch)
        if request.method == 'POST':
            action = request.POST.get('action')
            try:
                if action == 'upload':
                    upload = UploadForm(request.POST, request.FILES)
                    if not upload.is_valid():
                        raise ValidationError(str(upload.errors))
                    f = upload.cleaned_data['file']
                    if f.size > 20*1024*1024:
                        raise ValidationError('Максимум 20 МБ.')
                    content = f.read()
                    rows = read_rows(content, upload.mapping(), sheet=upload.cleaned_data['sheet'], first_row=upload.cleaned_data['first_row'], color_rules=upload.cleaned_data['color_rules'] and upload.cleaned_data['kind']=='OWN')
                    saved_mapping = dict(upload.mapping(), _sheet=upload.cleaned_data['sheet'], _first_row=upload.cleaned_data['first_row'])
                    created = services.stage(batch, upload.cleaned_data['kind'], f.name, content, saved_mapping, rows, request.user)
                    messages.success(request, 'Файл загружен для проверки.' if created else 'Этот файл уже загружен; дубликатов нет.')
                elif action == 'import':
                    counts = services.import_own(batch, request.user)
                    messages.success(request, f'Новых: {counts["created"]}; дополнено: {counts["filled"]}; требуют проверки: {counts["review"]}.')
                elif action == 'decide':
                    services.decide(batch, request.POST.get('row'), request.POST.get('decision'), request.POST.get('note',''), request.user, request.POST.get('booking') or None, request.POST.get('corrected_number',''))
                elif action == 'close':
                    services.close(batch, request.user)
                    messages.success(request, 'Сверено. Теперь внесите номер, дату и сумму фактуры.')
                elif action == 'reopen':
                    reason = request.POST.get('reason','').strip()
                    if not reason:
                        raise ValidationError('Укажите причину исправления.')
                    with transaction.atomic():
                        batch = Reconciliation.objects.select_for_update().get(pk=pk)
                        if batch.received or batch.employee_paid:
                            raise ValidationError('Есть платежи. Исправление оплаченной сверки требует отдельной корректировки; суммы не будут переписаны.')
                        batch.state = 'DRAFT'
                        batch.save()
                        services.checkpoint(batch, request.user, 'Открыто для исправления: ' + reason)
                elif action == 'payment':
                    with transaction.atomic():
                        batch = Reconciliation.objects.select_for_update().get(pk=pk)
                        payment = PaymentForm(request.POST, instance=batch)
                        if not payment.is_valid():
                            raise ValidationError(str(payment.errors))
                        payment.save()
                        services.checkpoint(batch, request.user, 'Фактура / платежи обновлены')
                    messages.success(request, 'Фактура и платежи сохранены; создана новая версия Excel.')
                elif action == 'calculation':
                    with transaction.atomic():
                        batch = Reconciliation.objects.select_for_update().get(pk=pk)
                        services.require_open(batch)
                        form = CalculationForm(request.POST, instance=batch)
                        if not form.is_valid():
                            raise ValidationError(str(form.errors))
                        form.save()
                        services.checkpoint(batch, request.user, 'Параметры расчёта изменены')
                else:
                    raise ValidationError('Неизвестное действие.')
                return redirect('admin:reconciliation_workspace', pk)
            except (ValidationError, ValueError, KeyError, Row.DoesNotExist, Booking.DoesNotExist) as error:
                messages.error(request, str(error))
        batch.refresh_from_db()
        query = batch.rows.select_related('booking')
        if request.GET.get('status') in dict(Row._meta.get_field('decision').choices):
            query = query.filter(decision=request.GET['status'])
        search = request.GET.get('q','').strip()
        if search:
            query = query.filter(number__icontains=search)
        page = Paginator(query, 50).get_page(request.GET.get('page'))
        for row in page:
            row.net_display = services.row_net(row, batch.vat)
        context = dict(self.admin_site.each_context(request), title=str(batch), batch=batch, upload_form=upload,
            payment_form=payment, calculation_form=CalculationForm(instance=batch), page=page, totals=services.totals(batch), versions=batch.revisions.all(),
            decisions=Row._meta.get_field('decision').choices, review_count=batch.rows.filter(decision='REVIEW').count(),
            opts=self.model._meta)
        return TemplateResponse(request, 'admin/reconciliation/workspace.html', context)
