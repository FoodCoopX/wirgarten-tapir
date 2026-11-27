from unittest.mock import MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.core.services.mailman.mailing_list_unsubscriber import (
    MailingListUnsubscriber,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDeleteMemberApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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
        KeycloakUserManager.create_keycloak_user_if_necessary(
            to_delete, initial_password=None
        )
        self.client.force_login(user)

        kc = KeycloakUserManager.get_keycloak_client()
        keycloak_id = kc.get_user_id(to_delete.email)
        self.assertIsNotNone(keycloak_id)

        url = reverse("coop:delete_member")
        url = f"{url}?member_id={to_delete.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(Member.objects.filter(id=to_delete.id).exists())

        keycloak_id = kc.get_user_id(to_delete.email)
        self.assertIsNone(keycloak_id)

    @patch.object(
        MailingListUnsubscriber, "unsubscribe_if_address_unused", autospec=True
    )
    def test_delete_memberWithExtras_unsubscribesMainAndConfirmedExtraAddressesAfterCommit(
        self, mock_unsubscribe_if_address_unused: MagicMock
    ):
        to_delete = MemberFactory.create(email="deleted@example.com")
        MemberExtraEmailFactory.create(
            member=to_delete, email="confirmed@example.com", confirmed_on=timezone.now()
        )
        MemberExtraEmailFactory.create(
            member=to_delete, email="unconfirmed@example.com", confirmed_on=None
        )
        self.client.force_login(MemberFactory.create(is_superuser=True))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(
                f"{reverse('coop:delete_member')}?member_id={to_delete.id}"
            )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {"deleted@example.com", "confirmed@example.com"},
            {
                call.kwargs["email"]
                for call in mock_unsubscribe_if_address_unused.call_args_list
            },
        )
