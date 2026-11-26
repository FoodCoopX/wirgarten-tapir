from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from tapir.accounts.models import TapirUser
from tapir.mail.config import MAIL_URL_PREFIX
from tapir.wirgarten.middleware.mailing import TapirMailPermissionMiddleware
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TapirMailPermissionMiddlewareTest(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = TapirUser(
            username="testuser", email="test@example.com", password="top_secret"
        )
        self.user.save()
        self.middleware = TapirMailPermissionMiddleware(
            get_response=lambda request: None
        )
        self.tracking_url = f"/{MAIL_URL_PREFIX}/api/tracking/12345/track"
        self.other_url = f"/{MAIL_URL_PREFIX}"

    def test_tapirMailPermissionMiddleWare_publicTrackingAccess_requestIsPassedThrough(
        self,
    ):
        request = self.factory.get(self.tracking_url)
        response = self.middleware(request)
        self.assertIsNone(response)

    def test_tapirMailPermissionMiddleWare_nonPublicPathWithoutPermission_permissionDeniedExceptionThrown(
        self,
    ):
        request = self.factory.get(self.other_url)
        self.user.is_superuser = False
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            self.middleware(request)

    def test_tapirMailPermissionMiddleWare_nonPublicPathWithPermission_requestIsPassedThrough(
        self,
    ):
        self.user.is_superuser = True
        request = self.factory.get(self.other_url)
        request.user = self.user
        response = self.middleware(request)

        self.assertIsNone(response)
