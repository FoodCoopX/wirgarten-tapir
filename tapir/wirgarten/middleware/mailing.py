import re
from django.conf import settings
from django.core.exceptions import PermissionDenied

from tapir.wirgarten.constants import Permission


class TapirMailPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # PUBLIC TRACKING PIXEL LINK ACCESS
        if re.match(
            settings.TAPIR_MAIL_PATH + r"/?api/tracking/(.*)/track/?", request.path
        ):
            return self.get_response(request)

        # REQUIRE PERMISSION FOR ALL OTHER PATHS
        if request.path.startswith(
            settings.TAPIR_MAIL_PATH
        ) and not request.user.has_perm(Permission.Email.MANAGE):
            raise PermissionDenied()

        return self.get_response(request)
