import json

from django.test import override_settings

from tapir.mail.config import MAIL_URL_PREFIX
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class MailUiViewTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @override_settings(SITE_URL="https://tapir.example.com")
    def test_get_default_rendersEnvironmentVariablesForTheMailUi(self):
        self._login_as_admin()

        response = self.client.get(f"/{MAIL_URL_PREFIX}/editor/123")

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "REACT_APP_API_ROOT": "https://tapir.example.com/tapirmail",
                "REACT_APP_BASENAME": "/tapirmail",
            },
            response.context["env_vars"],
        )
        self.assertContains(
            response,
            f'<script id="tapir-mail-env" type="application/json">{json.dumps(response.context["env_vars"])}</script>',
            html=False,
        )

    def test_get_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(f"/{MAIL_URL_PREFIX}/editor/123")

        self.assertStatusCode(response, 403)
