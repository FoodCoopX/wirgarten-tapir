import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentTransactionFactory,
    PaymentFactory,
    MandateReferenceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentTransactionDetailsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.transaction = PaymentTransactionFactory.create()

    def test_list_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse(
            "payments:payment_transaction_details",
        )
        url = f"{url}?transaction_id={self.transaction.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_list_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse(
            "payments:payment_transaction_details",
        )
        url = f"{url}?transaction_id={self.transaction.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_default_serializerFieldsFilledCorrectly(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        mandate_ref_1 = MandateReferenceFactory.create(ref="test_ref1")
        PaymentFactory.create(
            transaction=self.transaction,
            amount=12.7,
            mandate_ref=mandate_ref_1,
            subscription_payment_range_start=datetime.date.today(),
            subscription_payment_range_end=datetime.date.today(),
        )
        PaymentFactory.create(
            transaction=self.transaction,
            amount=8.5,
            mandate_ref=mandate_ref_1,
            subscription_payment_range_start=datetime.date.today(),
            subscription_payment_range_end=datetime.date.today(),
        )
        payment_ref_2 = PaymentFactory.create(
            transaction=self.transaction,
            amount=9.2,
            mandate_ref__ref="test_ref2",
            subscription_payment_range_start=datetime.date.today(),
            subscription_payment_range_end=datetime.date.today(),
        )
        PaymentFactory.create(
            transaction=PaymentTransactionFactory.create(),
            subscription_payment_range_start=datetime.date.today(),
            subscription_payment_range_end=datetime.date.today(),
        )

        url = reverse(
            "payments:payment_transaction_details",
        )
        url = f"{url}?transaction_id={self.transaction.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        payments = response_content["payments_by_mandate_ref"]

        self.assertEqual(2, len(payments))
        self.assertEqual(2, len(payments["test_ref1"]["payments"]))
        self.assertEqual(1, len(payments["test_ref2"]["payments"]))
        self.assertEqual(payment_ref_2.id, payments["test_ref2"]["payments"][0]["id"])

        members = response_content["members_by_mandate_ref"]
        self.assertEqual(2, len(members))
        self.assertEqual(mandate_ref_1.member.id, members["test_ref1"]["id"])
        self.assertEqual(
            payment_ref_2.mandate_ref.member.id, members["test_ref2"]["id"]
        )

        intended_uses = response_content["intended_use_by_mandate_ref"]
        self.assertEqual(
            {
                "test_ref1": f"Standort Name, {mandate_ref_1.member.last_name}, Verträge",
                "test_ref2": f"Standort Name, {payment_ref_2.mandate_ref.member.last_name}, Verträge",
            },
            intended_uses,
        )
