import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class MemberAssociationDepositViewTestCase(TapirIntegrationTest):
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
        self.member = MemberFactory.create(
            sepa_consent=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC)
        )
        self.membership = AssociationMembershipFactory.create(
            member=self.member, start_date=datetime.date(2026, 11, 1)
        )
        AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=self.member,
            amount=Decimal("200"),
            start_date=self.membership.start_date,
            actor=self.member,
            cache={},
        )
        self.client.force_login(self.member)
        self.url = reverse(
            "associations:member_association_deposit", args=[self.member.pk]
        )
