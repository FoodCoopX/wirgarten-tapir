from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentTransactionFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentTransactionViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_list_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:payment_transactions-list"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_list_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:payment_transactions-list"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_default_serializerFieldsFilledCorrectly(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        transaction = PaymentTransactionFactory.create()
        PaymentFactory.create(transaction=transaction, amount=12.7)
        PaymentFactory.create(transaction=transaction, amount=8.5)

        response = self.client.get(
            reverse("payments:payment_transactions-detail", args=[transaction.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual(2, response_content["payments_count"])
        self.assertEqual(21.2, response_content["payments_sum"])
        self.assertEqual(
            f"/tapir/admin/exportedfiles/{transaction.csv_file_id}/download",
            response_content["csv_download_url"],
        )
        self.assertEqual(
            f"/tapir/admin/exportedfiles/{transaction.xml_file_id}/download",
            response_content["xml_download_url"],
        )
