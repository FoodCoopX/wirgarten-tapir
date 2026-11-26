import re

from django.core.exceptions import PermissionDenied

from tapir.mail.config import MAIL_URL_PREFIX
from tapir.wirgarten.constants import Permission

MAIL_URL_PATH = f"/{MAIL_URL_PREFIX}"


class TapirMailPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # PUBLIC TRACKING PIXEL LINK ACCESS
        if (
            re.match(MAIL_URL_PATH + r"/?api/tracking/(.*)/track/?", request.path)
            or re.match(
                MAIL_URL_PATH + r"/?api/media_library/get_file/(.*)",
                request.path,
            )
            or re.match(MAIL_URL_PATH + r"/external/.*", request.path)
        ):
            return self.get_response(request)

        # REQUIRE PERMISSION FOR ALL OTHER PATHS
        if request.path.startswith(MAIL_URL_PATH) and not request.user.has_perm(
            Permission.Email.MANAGE
        ):
            raise PermissionDenied()

        return self.get_response(request)
