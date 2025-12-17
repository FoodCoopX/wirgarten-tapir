from django.urls import reverse
from rest_framework import status

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetMemberDetailsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_get_normalMemberTriesToGetData_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("coop:get_member_details")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_adminTriesToGetData_returnsMemberData(self):
        other_member = MemberFactory.create()
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        url = reverse("coop:get_member_details")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(other_member.id, response.json()["id"])
