from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberImportTemplateView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_anonymous_redirectsToLogin(self):
        self.assertStatusCode(
            self.client.get(reverse("utils:member_import_template")), 302
        )

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        self.assertStatusCode(
            self.client.get(reverse("utils:member_import_template")), 403
        )

    def test_get_loggedInAsAdmin_receivesCsv(self):
        self._login_as_admin()
        response = self.client.get(reverse("utils:member_import_template"))
        self.assertStatusCode(response, 200)
        self.assertEqual("text/csv; charset=utf-8", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbfNr;"))
