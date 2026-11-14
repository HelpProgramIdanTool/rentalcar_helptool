"""The operator language is independent of customer and supplier messages."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from customers.models import OperatorPreference


class OperatorLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = 'ru'
        if request.user.is_authenticated and not request.path.startswith(('/partners/', '/admin/')):
            language = OperatorPreference.objects.filter(user=request.user).values_list('language', flat=True).first() or 'ru'
        with translation.override(language):
            request.LANGUAGE_CODE = language
            response = self.get_response(request)
            response.headers.setdefault('Content-Language', language)
            return response


@login_required
@require_POST
def set_operator_language(request):
    language = request.POST.get('language')
    if language in {'ru', 'pl', 'en'}:
        OperatorPreference.objects.update_or_create(user=request.user, defaults={'language': language})
    target = request.POST.get('next', '/')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = '/'
    return redirect(target)
