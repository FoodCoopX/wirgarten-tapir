import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssociationDepositPaymentCreator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, 5)
        self.member = MemberFactory(
            sepa_consent=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
        )

    def test_createDepositAndPayment_default_linksScheduledPaymentToMemberDeposit(self):
        payment = AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=self.member,
            amount=Decimal("200"),
            start_date=datetime.date(2027, 1, 6),
            actor=self.member,
            cache={},
        )
        self.assertEqual(payment.association_deposit.member, self.member)
        self.assertEqual(payment.type, PAYMENT_TYPE_ASSOCIATION_DEPOSIT)
        self.assertEqual(payment.due_date, datetime.date(2027, 2, 5))

    def test_validateNewDeposit_memberAlreadyHasDeposit_rejectsSameOrDifferentAmount(
        self,
    ):
        AssociationDeposit.objects.create(member=self.member)
        for amount in (Decimal("200"), Decimal("250")):
            with self.subTest(amount=amount), self.assertRaisesMessage(
                ValidationError, "bereits eine Einlage"
            ):
                AssociationDepositPaymentCreator.validate_new_deposit(
                    member=self.member, amount=amount, cache={}
                )

    def test_validateNewDeposit_depositsDisabled_rejectsBeforeOtherValidation(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        AssociationDeposit.objects.create(member=self.member)
        with self.assertRaisesMessage(ValidationError, "nicht aktiviert"):
            AssociationDepositPaymentCreator.validate_new_deposit(
                member=self.member, amount=Decimal("0"), cache={}
            )

    def test_validateNewDeposit_missingConsent_raisesError(self):
        self.member.sepa_consent = None
        with self.assertRaisesMessage(ValidationError, "gültige SEPA-Zustimmung"):
            AssociationDepositPaymentCreator.validate_new_deposit(
                member=self.member, amount=Decimal("200"), cache={}
            )
