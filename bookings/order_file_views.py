from collections import Counter
from uuid import UUID
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import OrderFileSync
from .statistics import can_view_statistics
from .order_file import prepare_sync, apply_sync, export_sync


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def order_file(request):
    if not can_view_statistics(request.user):
        raise PermissionDenied
    error=''
    current=None
    if request.method=='POST':
        try:
            if request.POST.get('action')=='apply':
                current=get_object_or_404(OrderFileSync,pk=request.POST.get('run'))
                if request.POST.get('confirm')!='yes':
                    raise ValidationError('Подтвердите применение проверенных строк.')
                current=apply_sync(current,request.user)
                return redirect('quotes:order_file')
            elif request.POST.get('action')=='export':
                current=export_sync(request.user)
                return redirect('quotes:order_file_download',pk=current.pk)
            elif request.POST.get('action')=='preview':
                upload=request.FILES.get('file')
                if not upload:
                    raise ValidationError('Выберите общий Excel.')
                if upload.size>15*1024*1024:
                    raise ValidationError('Файл больше 15 MB.')
                current=prepare_sync(request.user,upload.read())
            else:
                raise ValidationError('Неизвестное действие.')
        except (ValidationError,ValueError,TimeoutError,OSError) as exc:
            error='; '.join(exc.messages) if isinstance(exc,ValidationError) else 'Не удалось выполнить операцию. Повторите проверку.'
    rows=current.plan['rows'] if current else []
    return render(request,'bookings/order_file.html',{
        'active_menu':'order_file','error':error,'current':current,'rows':rows,
        'counts':dict(Counter(row['action'] for row in rows)),
        'runs':OrderFileSync.objects.all()[:12]})


@login_required
@never_cache
def download(request,pk):
    if not can_view_statistics(request.user):
        raise PermissionDenied
    run=get_object_or_404(OrderFileSync,pk=pk,applied=True)
    if not run.result:
        raise Http404
    return FileResponse(run.result.open('rb'),as_attachment=True,filename='All_orders.xlsx')
