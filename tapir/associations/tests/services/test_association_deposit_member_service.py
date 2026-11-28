import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDepositTransaction
from tapir.associations.services.association_deposit_member_service import (
    AssociationDepositMemberService,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositMemberService(TapirIntegrationTest):
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
        self.member = MemberFactory.create(
            sepa_consent=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC)
        )
        self.membership = AssociationMembershipFactory.create(
            member=self.member, start_date=datetime.date(2026, 11, 1)
        )
        AssociationDepositTransaction.objects.create(
            member=self.member,
            transaction_type=AssociationDepositTransaction.Type.IMPORT,
            amount=200,
            valid_at=self.membership.start_date,
        )

    def test_getAmount_importedBalanceAndIncrease_sumsTransactions(self):
        AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=self.member,
            amount=Decimal("50"),
            start_date=self.membership.start_date,
            actor=self.member,
            cache={},
        )
        self.assertEqual(250, AssociationDepositMemberService.get_amount(self.member))

    def test_getDetails_individualAgreement_reportsRequest(self):
        self.membership.deposit_agreement_requested_at = datetime.datetime(
            2026, 11, 1, tzinfo=datetime.UTC
        )
        self.membership.save()
        self.assertTrue(
            AssociationDepositMemberService.get_details(member=self.member, cache={})[
                "agreement_requested"
            ]
        )

    def test_validateIncrease_default_returnsDifference(self):
        self.assertEqual(
            Decimal("50"),
            AssociationDepositMemberService.validate_increase(
                member=self.member, total_amount=Decimal("250"), cache={}
            ),
        )

    def test_validateIncrease_unchangedOrLowerTotal_raisesError(self):
        for total in (Decimal("200"), Decimal("150")):
            with self.subTest(total=total), self.assertRaises(ValidationError):
                AssociationDepositMemberService.validate_increase(
                    member=self.member, total_amount=total, cache={}
                )

    def test_validateIncrease_inactiveMembership_raisesError(self):
        self.membership.end_date = datetime.date(2026, 11, 4)
        self.membership.save()
        with self.assertRaisesMessage(ValidationError, "aktive Vereinsmitgliedschaft"):
            AssociationDepositMemberService.validate_increase(
                member=self.member, total_amount=Decimal("250"), cache={}
            )

    def test_validateIncrease_disabledFeature_raisesError(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        with self.assertRaisesMessage(ValidationError, "nicht aktiviert"):
            AssociationDepositMemberService.validate_increase(
                member=self.member, total_amount=Decimal("250"), cache={}
            )

    def test_validateIncrease_noSepaConsent_raisesError(self):
        self.member.sepa_consent = None
        with self.assertRaisesMessage(ValidationError, "SEPA-Zustimmung"):
            AssociationDepositMemberService.validate_increase(
                member=self.member, total_amount=Decimal("250"), cache={}
            )
