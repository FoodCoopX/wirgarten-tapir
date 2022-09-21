import datetime

from django.conf import settings
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class ClientPermsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_anonymous:
            return

        request_comes_from_welcome_desk = (
            request.META.get("HTTP_X_SSL_CLIENT_VERIFY") == "SUCCESS"
            and request.META["HTTP_X_SSL_CLIENT_S_DN"]
            in settings.CLIENT_PERMISSIONS.keys()
        )
        if request_comes_from_welcome_desk:
            request.user.client_perms = settings.CLIENT_PERMISSIONS[
                request.META["HTTP_X_SSL_CLIENT_S_DN"]
            ]
            return
