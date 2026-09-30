import datetime

from django.urls import reverse
from rest_framework import status

from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MandateReferenceFactory,
    MemberFactory,
    PaymentFactory,
    PaymentTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMembersNeedingBankingDataForRebuildApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2023, month=4, day=15)
        )

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self._do_call(from_date="2023-04-01")

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_default_memberWithPaymentInRangeMissingIban_isReturned(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member = self._create_member_with_banking_data(first_name="Anna", iban=None)
        self._create_payment_for_member(member, month=datetime.date(2023, 4, 1))

        response = self._do_call(from_date="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIn("Anna", {entry["first_name"] for entry in response.json()})

    def test_get_default_memberWithCompleteBankingData_isNotReturned(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member = self._create_member_with_banking_data(first_name="Anna")
        self._create_payment_for_member(member, month=datetime.date(2023, 4, 1))

        response = self._do_call(from_date="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json())

    def test_get_default_paymentBeforeFromDate_isNotReturned(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member = self._create_member_with_banking_data(first_name="Anna", iban=None)
        self._create_payment_for_member(member, month=datetime.date(2023, 3, 1))

        response = self._do_call(from_date="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json())

    def test_get_default_paymentAfterToday_isNotReturned(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member = self._create_member_with_banking_data(first_name="Anna", iban=None)
        self._create_payment_for_member(member, month=datetime.date(2023, 5, 1))

        response = self._do_call(from_date="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json())

    def test_get_default_coopSharePayment_isNotReturned(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member = self._create_member_with_banking_data(first_name="Anna", iban=None)
        self._create_payment_for_member(
            member, month=datetime.date(2023, 4, 1), type=PAYMENT_TYPE_COOP_SHARES
        )

        response = self._do_call(from_date="2023-04-01")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json())

    @staticmethod
    def _create_member_with_banking_data(**kwargs):
        kwargs.setdefault("iban", "DE89370400440532013000")
        kwargs.setdefault("account_owner", "Test Owner")
        kwargs.setdefault(
            "sepa_consent",
            datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc),
        )
        return MemberFactory.create(**kwargs)

    @staticmethod
    def _create_payment_for_member(member, month: datetime.date, type: str = "Test"):
        transaction = PaymentTransactionFactory.create(month=month)
        mandate_ref = MandateReferenceFactory.create(member=member)
        return PaymentFactory.create(
            transaction=transaction, mandate_ref=mandate_ref, type=type
        )

    def _do_call(self, from_date: str):
        url = reverse("payments:members_needing_banking_data_for_rebuild")
        url = f"{url}?from={from_date}"
        return self.client.get(url)
