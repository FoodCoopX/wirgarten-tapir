from tapir.mail.config import MAIL_URL_PREFIX
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class FilepondPermissionsTest(TapirIntegrationTest):
    def test_load_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(
            f"/{MAIL_URL_PREFIX}/api/media_library/filepond/load/"
        )

        self.assertStatusCode(response, 403)
