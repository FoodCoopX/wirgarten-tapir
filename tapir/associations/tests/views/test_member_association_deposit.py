import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberAssociationDepositView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        self.member = MemberFactory(
            sepa_consent=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC)
        )
        membership = AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2026, 11, 1)
        )
        AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=self.member,
            amount=Decimal("200"),
            start_date=membership.start_date,
            actor=self.member,
            cache={},
        )
        self.client.force_login(self.member)
        self.url = reverse(
            "associations:member_association_deposit", args=[self.member.pk]
        )

    def test_post_confirmedIncrease_createsOnlyDifferenceEvenOnRetry(self):
        data = {"total_amount": "250", "previous_amount": "200", "confirmation": True}
        for _ in range(2):
            response = self.client.post(self.url, data, content_type="application/json")
            self.assertEqual(200, response.status_code, response.content)
            self.assertEqual(250, response.json()["amount"])
        self.assertCountEqual(
            [Decimal("50"), Decimal("200")],
            AssociationDeposit.objects.get().payments.values_list("amount", flat=True),
        )

    def test_post_staleAmountOrMissingConfirmation_createsNoDebit(self):
        for data in (
            {"total_amount": "250", "previous_amount": "150", "confirmation": True},
            {"total_amount": "250", "previous_amount": "200", "confirmation": False},
        ):
            with self.subTest(data=data):
                self.assertEqual(
                    400,
                    self.client.post(
                        self.url, data, content_type="application/json"
                    ).status_code,
                )
        self.assertEqual(
            [Decimal("200")],
            list(
                AssociationDeposit.objects.get().payments.values_list(
                    "amount", flat=True
                )
            ),
        )

    def test_get_otherMember_returns403(self):
        self.client.force_login(MemberFactory())
        self.assertEqual(403, self.client.get(self.url).status_code)

    def test_post_otherMember_returns403(self):
        self.client.force_login(MemberFactory())

        response = self.client.post(
            self.url,
            {"total_amount": "250", "previous_amount": "200", "confirmation": True},
            content_type="application/json",
        )

        self.assertStatusCode(response, 403)
