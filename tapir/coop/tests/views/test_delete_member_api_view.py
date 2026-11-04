from django.db import connection
from django.urls import reverse
from rest_framework import status

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.wirgarten.models import CoopShareTransaction, Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    CoopShareTransactionFactory,
    MemberFactory,
)
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

    def test_delete_otherMemberHasTransferFromDeletedMember_otherTransactionKept(self):
        to_delete = MemberFactory.create()
        partner = MemberFactory.create()
        transaction_type = CoopShareTransaction.CoopShareTransactionType
        CoopShareTransactionFactory.create(
            member=to_delete,
            transaction_type=transaction_type.TRANSFER_OUT,
            quantity=-1,
            transfer_member=partner,
            payment=None,
        )
        partner_transaction = CoopShareTransactionFactory.create(
            member=partner,
            transaction_type=transaction_type.TRANSFER_IN,
            quantity=1,
            transfer_member=to_delete,
            payment=None,
        )
        self.client.force_login(MemberFactory.create(is_superuser=True))

        url = f"{reverse('coop:delete_member')}?member_id={to_delete.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        # Foreign keys are checked at commit, which a test transaction never reaches
        connection.check_constraints()
        partner_transaction.refresh_from_db()
        self.assertIsNone(partner_transaction.transfer_member)
        self.assertEqual(1, partner_transaction.quantity)
