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
        AssociationDepositPaymentCreator.create_payment(
            membership, Decimal("200"), self.member, {}
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
            AssociationDeposit.objects.values_list("payment__amount", flat=True),
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
        self.assertEqual(1, AssociationDeposit.objects.count())

    def test_get_otherMember_returns403(self):
        self.client.force_login(MemberFactory())
        self.assertEqual(403, self.client.get(self.url).status_code)
