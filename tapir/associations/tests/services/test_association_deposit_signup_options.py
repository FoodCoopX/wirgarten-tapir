import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import override_settings
from django.urls import reverse

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementAuthorizedLogEntry,
    AssociationDepositHardshipRequestedLogEntry,
)
from tapir.associations.services.association_deposit_agreement_creator import (
    AssociationDepositAgreementCreator,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


@override_settings(
    SITE_URL="http://tapir.test:8000",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_AUTO_BCC="",
)
class TestAssociationDepositSignupOptions(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        self._set_parameter(ParameterKeys.SITE_ADMIN_EMAIL, "admin@example.test")
        self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, 5)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.today = datetime.date(2026, 11, 5)
        self.member = MemberFactory()
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
        )

    def signup(self, option, amount=None, has_products=True):
        return AssociationDepositSignupHandler.create_signup_deposit(
            self.member,
            amount,
            self.today,
            has_products,
            self.member,
            {},
            payment_option=option,
            expected_instalments=(
                get_parameter_value(
                    ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, cache={}
                )
                if option == "standard_instalments"
                else None
            ),
        )

    def test_organisation_approved_standard_plan_needs_no_individual_authorization(
        self,
    ):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        self.signup("standard_instalments", Decimal("200"))
        self.signup("standard_instalments", Decimal("200"))
        account = AssociationDepositAccount.objects.get()
        self.assertEqual(4, account.instalment_count)
        self.assertFalse(account.is_individual_agreement)
        self.assertEqual(
            [Decimal("50")] * 4,
            list(
                account.payments.order_by("due_date").values_list("amount", flat=True)
            ),
        )
        self.assertEqual(
            [
                datetime.date(2026, 11, 5),
                datetime.date(2026, 12, 5),
                datetime.date(2027, 1, 5),
                datetime.date(2027, 2, 5),
            ],
            list(
                account.payments.order_by("due_date").values_list("due_date", flat=True)
            ),
        )
        self.assertFalse(AssociationDepositAgreementAuthorizedLogEntry.objects.exists())

    def test_standard_option_cannot_bypass_amount_or_count_rules(self):
        with self.assertRaisesMessage(ValidationError, "nicht freigegeben"):
            self.signup("standard_instalments", Decimal("200"))
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        for amount in [
            None,
            Decimal("0"),
            Decimal("100"),
            Decimal("225"),
            Decimal("250"),
        ]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                self.signup("standard_instalments", amount)
        with self.assertRaisesMessage(ValidationError, "nicht freigegeben"):
            AssociationDepositAgreementCreator.create_regular_agreement(
                self.member,
                Decimal("200"),
                self.today,
                self.member,
                {},
                instalment_count=2,
            )
        with self.assertRaises(ValidationError):
            self.signup("custom_instalments", Decimal("200"))
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_higher_standard_total_requires_existing_larger_signup_permission(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, True)
        self.signup("standard_instalments", Decimal("250"))
        self.assertEqual(
            [Decimal("62.50")] * 4,
            list(Payment.objects.values_list("amount", flat=True)),
        )

    def test_optional_supporting_member_can_omit_deposit_without_silent_standard_plan(
        self,
    ):
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED, False
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        self.signup("once", has_products=False)
        with self.assertRaises(ValidationError):
            self.signup("standard_instalments", has_products=False)
        self.assertFalse(AssociationDepositAccount.objects.exists())

    def test_changed_defaults_do_not_modify_or_reclassify_existing_plan(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        self.signup("standard_instalments", Decimal("200"))
        before = list(Payment.objects.order_by("pk").values())
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, "6")
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, False
        )
        account = AssociationDepositAgreementCreator.create_regular_agreement(
            self.member, Decimal("200"), self.today, self.member, {}, instalment_count=4
        )
        self.assertFalse(account.is_individual_agreement)
        self.assertEqual(before, list(Payment.objects.order_by("pk").values()))

    def test_unreasonable_counts_rejected_before_due_date_work_or_allocation(self):
        for count in [0, 121, 10**9, True]:
            with self.subTest(count=count), patch(
                "tapir.associations.services.association_deposit_instalment_calculator.PaymentDueDateCalculator.get_first_due_date_on_or_after"
            ) as dates:
                with self.assertRaises(ValidationError):
                    AssociationDepositInstalmentCalculator.build_payment_schedule(
                        Decimal("999999.99"), count, self.today, {}
                    )
                dates.assert_not_called()
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, True)
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, str(10**9)
        )
        with self.assertRaises(ValidationError):
            self.signup("standard_instalments", Decimal("200"))
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_hardship_is_opt_in_and_never_assumes_an_amount(self):
        with self.assertRaisesMessage(ValidationError, "nicht aktiviert"):
            self.signup("hardship")
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        for amount in [Decimal("0"), Decimal("100"), Decimal("200")]:
            with self.subTest(amount=amount), self.assertRaisesMessage(
                ValidationError, "kein Einlagenbetrag"
            ):
                self.signup("hardship", amount)
        self.signup("hardship")
        account = AssociationDepositAccount.objects.get()
        self.assertIsNone(account.agreed_amount)
        self.assertIsNone(account.effective_from)
        self.assertIsNotNone(account.hardship_requested_at)
        self.assertFalse(account.is_individual_agreement)
        self.assertFalse(Payment.objects.exists())

    def test_one_notification_only_after_commit_and_no_duplicate_on_retry(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.signup("hardship")
            self.signup("hardship")
            self.assertEqual(0, len(mail.outbox))
        self.assertEqual(1, len(callbacks))
        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(["admin@example.test"], mail.outbox[0].to)
        self.assertIn(
            "http://tapir.test:8000"
            + reverse(
                "associations:deposit_case", kwargs={"member_id": self.member.pk}
            ),
            mail.outbox[0].body,
        )
        self.assertIn("kein Einzug", mail.outbox[0].body)

    def test_missing_admin_email_keeps_case_without_scheduling_notification(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        self._set_parameter(ParameterKeys.SITE_ADMIN_EMAIL, "")
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.signup("hardship")
        self.assertEqual([], callbacks)
        self.assertEqual(0, len(mail.outbox))
        self.assertIsNotNone(
            AssociationDepositAccount.objects.get().hardship_requested_at
        )

    def test_rollback_discards_case_audit_and_notification(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.signup("hardship")
                raise RuntimeError("Bestellung zurückgerollt")
        self.assertEqual([], callbacks)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(AssociationDepositHardshipRequestedLogEntry.objects.exists())
        self.assertEqual(0, len(mail.outbox))

    def test_external_receipt_before_request_preserves_credit_without_debt_or_debit(
        self,
    ):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("25"),
            self.today,
            "bank-before-request",
            "Kontoauszug",
            self.member,
            {},
        )
        self.signup("hardship")
        self.signup("hardship")
        account = AssociationDepositAccount.objects.get()
        self.assertEqual(Decimal("25"), account.receipts.get().amount)
        self.assertIsNone(account.agreed_amount)
        self.assertFalse(Payment.objects.exists())

    def test_notification_failure_keeps_the_persistent_case(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        with patch(
            "tapir.associations.services.association_deposit_hardship_notifier.send_email",
            side_effect=RuntimeError("Mailversand nicht erreichbar"),
        ):
            with self.assertLogs(level="ERROR") as errors:
                with self.captureOnCommitCallbacks(execute=True):
                    self.signup("hardship")
        self.assertIn("Mailversand nicht erreichbar", "\n".join(errors.output))
        account = AssociationDepositAccount.objects.get()
        self.assertIsNotNone(account.hardship_requested_at)
        self.assertIsNone(account.agreed_amount)
        self.assertFalse(Payment.objects.exists())
