from django.core.exceptions import PermissionDenied
from django.conf import settings

from tapir.wirgarten.constants import Permission


class TapirMailPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(settings.TAPIR_MAIL_PATH):
            if not request.user.has_perm(Permission.Email.MANAGE):
                raise PermissionDenied

        return self.get_response(request)
