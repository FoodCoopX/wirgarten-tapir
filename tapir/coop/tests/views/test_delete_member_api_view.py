from django.urls import reverse
from rest_framework import status

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDeleteMemberApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_delete_normalMemberTriesToDelete_returns403(self):
        to_delete = MemberFactory.create()
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("coop:delete_member")
        url = f"{url}?member_id={to_delete.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Member.objects.filter(id=to_delete.id).exists())

    def test_delete_adminTriesToDelete_memberDeleted(self):
        to_delete = MemberFactory.create()
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        kc = KeycloakUserManager.get_keycloak_client(cache={})
        keycloak_id = kc.get_user_id(to_delete.email)
        self.assertIsNotNone(keycloak_id)

        url = reverse("coop:delete_member")
        url = f"{url}?member_id={to_delete.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(Member.objects.filter(id=to_delete.id).exists())

        keycloak_id = kc.get_user_id(to_delete.email)
        self.assertIsNone(keycloak_id)
