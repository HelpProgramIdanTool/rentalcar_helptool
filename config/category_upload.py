import json
import hashlib
from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from suppliers.form_categories import validate_mapping, apply_mapping


@admin.site.admin_view
@never_cache
@require_http_methods(['GET','POST'])
def category_upload(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Owner access required')
    result = None
    error = ''
    if request.method=='POST':
        try:
            source = request.FILES.get('mapping')
            if not source or source.size>512*1024:
                raise ValueError('Выберите JSON соответствий, до 512 КБ.')
            payload = json.loads(source.read())
            mapping = validate_mapping(payload)
            result = {'categories':len(mapping), 'memberships':sum(map(len,mapping.values())), 'applied':False}
            if request.POST.get('apply')=='yes':
                from suppliers.models import FormVehicleCategory, VehicleGroup
                folder=Path(settings.MEDIA_ROOT)/'category-mapping-backups'
                folder.mkdir(parents=True,exist_ok=True)
                previous=[{'name':c.name,'active':c.is_active,'group_ids':list(c.vehicle_groups.values_list('pk',flat=True))}
                          for c in FormVehicleCategory.objects.all()]
                path=folder/(uuid4().hex+'.json')
                visibility=list(VehicleGroup.objects.filter(pk__in=set().union(*mapping.values())).values('pk','show_in_offers'))
                path.write_text(json.dumps({'operator_user_id':request.user.pk,'previous':previous,'previous_group_visibility':visibility,
                    'approved_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()},ensure_ascii=True),encoding='utf8')
                path.chmod(0o600)
                result = {**apply_mapping(payload), 'applied':True}
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            error = str(exc)
        except Exception:
            error = 'Одна из фирм или групп не найдена. Ничего не применено; проверьте файл.'
    return render(request,'admin/category_upload.html',{'result':result,'error':error})
