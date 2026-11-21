from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDataDisclosurePdfApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def get_pdf(self, member_id: str):
        url = reverse("core:member_data_disclosure_pdf")
        return self.client.get(f"{url}?member_id={member_id}")

    def test_get_ownData_returnsPdf(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.get_pdf(member.id)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual("application/pdf", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_get_otherMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.get_pdf(member.id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
