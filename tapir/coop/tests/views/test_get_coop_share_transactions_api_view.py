from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetCoopShareTransactionsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberGetsTransactionsOfAnotherMember_returns403(self):
        logged_in_member = MemberFactory.create()
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("coop:get_coop_share_transactions")
        url = f"{url}?member={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_memberGetsOwnTransactions_returns200(self):
        transaction = CoopShareTransactionFactory.create()
        self.client.force_login(transaction.member)

        url = reverse("coop:get_coop_share_transactions")
        url = f"{url}?member_id={transaction.member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        transactions = response_content["transactions"]
        self.assertEqual(1, len(transactions))
        self.assertEqual(transaction.id, transactions[0]["id"])

    def test_get_adminGetsTransactionsOfAnotherMember_returns200(self):
        transaction = CoopShareTransactionFactory.create()
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        url = reverse("coop:get_coop_share_transactions")
        url = f"{url}?member_id={transaction.member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        transactions = response_content["transactions"]
        self.assertEqual(1, len(transactions))
        self.assertEqual(transaction.id, transactions[0]["id"])
