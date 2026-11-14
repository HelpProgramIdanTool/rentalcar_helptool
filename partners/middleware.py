from django.http import HttpResponseForbidden
from .models import PartnerAccess


class PartnerBoundaryMiddleware:
    """Partner credentials must never grant access to operator-only views."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            access = PartnerAccess.objects.filter(user=request.user).first()
            login_path = request.path_info in ('/partners/login/', '/partners/logout/')
            if access and (not request.path_info.startswith('/partners/') or (not access.is_active and not login_path)):
                return HttpResponseForbidden('אין הרשאה לעמוד זה.')
        return self.get_response(request)
