import datetime
from unittest.mock import Mock, patch

from django.urls import reverse
from rest_framework import status

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.payments.services.subscription_payments_rebuilder import (
    SubscriptionPaymentsRebuilder,
)
from tapir.wirgarten.models import Payment, PaymentTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MandateReferenceFactory,
    MemberFactory,
    PaymentFactory,
    PaymentTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMembersWithoutIbanForRebuildMonthApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self._do_call(month="2023-04-01")

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    @patch.object(
        SubscriptionPaymentsRebuilder, "delete_existing_contract_payments_from"
    )
    @patch.object(MonthPaymentBuilder, "build_payments_for_month", autospec=True)
    def test_get_default_onlyReturnsDistinctMembersWithoutIban(
        self, mock_build_payments_for_month: Mock, mock_delete_existing: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member_with_iban = MemberFactory.create(iban="DE89370400440532013000")
        member_without_iban = MemberFactory.create(
            first_name="Anna", last_name="Müller", iban=None
        )

        mandate_ref_with_iban = MandateReferenceFactory.create(member=member_with_iban)
        mandate_ref_without_iban = MandateReferenceFactory.create(
            member=member_without_iban
        )

        # member_without_iban appears twice (two payments), should only be returned once
        mock_build_payments_for_month.return_value = [
            Payment(mandate_ref=mandate_ref_with_iban, amount=10, type="Vertrag"),
            Payment(mandate_ref=mandate_ref_without_iban, amount=20, type="Vertrag"),
            Payment(mandate_ref=mandate_ref_without_iban, amount=30, type="Vertrag"),
        ]

        response = self._do_call(month="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(1, len(response_content))
        self.assertEqual("Anna", response_content[0]["first_name"])
        self.assertEqual("Müller", response_content[0]["last_name"])

        mock_delete_existing.assert_called_once_with(datetime.date(2023, 4, 1))
        mock_build_payments_for_month.assert_called_once_with(
            reference_date=datetime.date(2023, 4, 1), cache={}, generated_payments=set()
        )

    @patch.object(MonthPaymentBuilder, "build_payments_for_month", autospec=True)
    def test_get_default_doesNotPersistDeletionOfExistingPayments(
        self, mock_build_payments_for_month: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        mock_build_payments_for_month.return_value = []

        transaction = PaymentTransactionFactory.create(month=datetime.date(2023, 4, 1))
        PaymentFactory.create(transaction=transaction)
        transaction_count_before = PaymentTransaction.objects.count()
        payment_count_before = Payment.objects.count()

        response = self._do_call(month="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(transaction_count_before, PaymentTransaction.objects.count())
        self.assertEqual(payment_count_before, Payment.objects.count())

    def _do_call(self, month: str):
        url = reverse("payments:members_without_iban_for_rebuild_month")
        url = f"{url}?month={month}"
        return self.client.get(url)
