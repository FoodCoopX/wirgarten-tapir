import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositIncreasedLogEntry,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_increase_recorder import (
    AssociationDepositIncreaseRecorder,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import Payment, ExportedFile
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositSignup(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.today = datetime.date(2026, 11, 5)
        self.member = MemberFactory()
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
        )

    def signup(self, amount=Decimal("200"), has_products=True):
        return AssociationDepositSignupHandler.create_signup_deposit(
            self.member, amount, self.today, has_products, self.member, {}
        )

    def enable(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)

    def test_disabled_by_default_does_not_create_agreement_or_debit(self):
        self.signup(amount=None)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())
        with self.assertRaisesMessage(ValidationError, "nicht aktiviert"):
            self.signup()

    def test_enabling_and_reading_existing_member_never_creates_debt(self):
        self.enable()
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertTrue(details["visible"])
        self.assertIsNone(details["agreed_amount"])
        self.assertFalse(details["can_increase"])
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_regular_signup_and_retry_keep_one_agreement_and_payment(self):
        self.enable()
        self.signup()
        self.signup()
        self.assertEqual(1, AssociationDepositAccount.objects.count())
        payment = Payment.objects.get()
        self.assertEqual(Decimal("200"), payment.amount)
        self.assertGreaterEqual(payment.due_date, self.today)
        self.assertEqual(self.member.pk, payment.mandate_ref.member_id)

    def test_supporting_members_can_omit_deposit_only_if_configured(self):
        self.enable()
        with self.assertRaises(ValidationError):
            self.signup(None, has_products=False)
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED, False
        )
        self.signup(None, has_products=False)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())
        with self.assertRaises(ValidationError):
            self.signup(None, has_products=True)

    def test_signup_enforces_minimum_cents_increments_and_larger_amount_permission(
        self,
    ):
        self.enable()
        for amount in ["0", "100", "225", "200.001", "250"]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                self.signup(Decimal(amount))
        self.assertFalse(Payment.objects.exists())
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, True)
        self.signup(Decimal("250"))
        self.assertEqual(Decimal("250"), Payment.objects.get().amount)

    def test_disabled_export_preserves_pending_payment_and_history(self):
        self.enable()
        self.signup()
        before = list(Payment.objects.values())
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        self.assertEqual(
            [],
            PaymentExportBuilder.export_association_deposit_payments(
                datetime.date(2026, 12, 5), False, {}
            ),
        )
        self.assertEqual(before, list(Payment.objects.values()))
        self.assertFalse(ExportedFile.objects.exists())
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertTrue(details["visible"])
        self.assertEqual(Decimal("200"), details["agreed_amount"])
        self.assertFalse(details["can_increase"])

    def test_explicit_increase_updates_pending_payment_once_with_audit(self):
        self.enable()
        self.signup()
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        for _ in range(2):
            AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                self.member, Decimal("250"), self.member, {}
            )
        self.assertEqual(1, Payment.objects.count())
        self.assertEqual(Decimal("250"), Payment.objects.get().amount)
        log = AssociationDepositIncreasedLogEntry.objects.get()
        self.assertEqual("200.00", log.old_values["agreed_amount"])
        self.assertEqual("250", log.new_values["agreed_amount"])

    def test_increase_creates_only_difference_after_committed_payment(self):
        self.enable()
        self.signup()
        payment = Payment.objects.get()
        payment.status = Payment.PaymentStatus.PAID
        payment.save()
        original = list(Payment.objects.values())
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        AssociationDepositIncreaseRecorder.increase_agreed_deposit(
            self.member, Decimal("250"), self.member, {}
        )
        self.assertEqual(
            Decimal("50"), Payment.objects.exclude(pk=payment.pk).get().amount
        )
        self.assertEqual(original, list(Payment.objects.filter(pk=payment.pk).values()))

    def test_minimum_increase_never_changes_existing_agreement_or_payment(self):
        self.enable()
        self.signup()
        original = list(Payment.objects.values())
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, "300")
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(Decimal("200"), details["agreed_amount"])
        self.assertEqual(original, list(Payment.objects.values()))

    def test_unauthorized_amount_changes_leave_agreement_and_payment_unchanged(self):
        self.enable()
        self.signup()
        with self.assertRaises(ValidationError):
            AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                self.member, Decimal("250"), self.member, {}
            )
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        for value in ["150", "225", "250.001"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                    self.member, Decimal(value), self.member, {}
                )
        self.assertEqual(Decimal("200"), Payment.objects.get().amount)
        self.assertFalse(AssociationDepositIncreasedLogEntry.objects.exists())

    def test_failed_new_debit_rolls_back_increase_and_its_audit(self):
        self.enable()
        self.signup()
        payment = Payment.objects.get()
        payment.status = Payment.PaymentStatus.PAID
        payment.save()
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        type(self.member).objects.filter(pk=self.member.pk).update(sepa_consent=None)
        with self.assertRaisesMessage(ValidationError, "SEPA-Zustimmung"):
            AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                self.member, Decimal("250"), self.member, {}
            )
        self.assertEqual(
            Decimal("200"), AssociationDepositAccount.objects.get().agreed_amount
        )
        self.assertEqual(1, Payment.objects.count())
        self.assertFalse(AssociationDepositIncreasedLogEntry.objects.exists())
