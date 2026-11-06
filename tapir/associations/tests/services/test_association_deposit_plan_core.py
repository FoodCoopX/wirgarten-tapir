import datetime
import uuid
from unittest.mock import patch
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementAuthorizedLogEntry,
    AssociationDepositHardshipRequestedLogEntry,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_agreement_creator import (
    AssociationDepositAgreementCreator,
)
from tapir.associations.services.association_deposit_increase_recorder import (
    AssociationDepositIncreaseRecorder,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_hardship_request_recorder import (
    AssociationDepositHardshipRequestRecorder,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.tests.factories import AssociationDepositAccountFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentFactory,
    MandateReferenceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositPlanCore(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, 5)
        self.today = datetime.date(2026, 11, 5)
        self.member = MemberFactory(
            sepa_consent=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC)
        )
        self.admin = MemberFactory(is_superuser=True)
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
        )

    def test_external_receipt_reduces_oldest_of_four_open_rates(self):
        account = AssociationDepositAccountFactory(
            member=self.member,
            agreed_amount=200,
            effective_from=self.today,
            instalment_count=4,
        )
        mandate = MandateReferenceFactory(member=self.member)
        payments = [
            PaymentFactory(
                association_deposit_account=account,
                mandate_ref=mandate,
                amount=50,
                due_date=(
                    datetime.date(2026, 11 + index, 5)
                    if index < 2
                    else datetime.date(2027, index - 1, 5)
                ),
                instalment_number=index + 1,
                transaction=None,
                status=Payment.PaymentStatus.DUE,
            )
            for index in range(4)
        ]
        AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("25"),
            self.today,
            "receipt-rate-1",
            "Kontoauszug",
            self.member,
            {},
        )
        self.assertEqual(
            [Decimal("25"), Decimal("50"), Decimal("50"), Decimal("50")],
            list(
                account.payments.order_by("due_date").values_list("amount", flat=True)
            ),
        )
        self.assertEqual(
            {payment.pk for payment in payments},
            set(account.payments.values_list("pk", flat=True)),
        )

    def authorize(self, **changes):
        account = AssociationDepositAccount.objects.filter(member=self.member).first()
        arguments = dict(
            member=self.member,
            amount=Decimal("200"),
            effective_from=self.today,
            instalment_count=4,
            consented_on=self.today,
            consent_note="Persönlich zugestimmt, Gespräch dokumentiert",
            expected_revision=account.agreement_revision if account else 0,
            request_key=uuid.uuid4(),
            actor=self.admin,
            cache={},
        )
        arguments.update(changes)
        return AssociationDepositAgreementAuthorizer.authorize_agreement(**arguments)

    def test_hardship_request_stays_unknown_without_payment_and_retry_is_idempotent(
        self,
    ):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        first = AssociationDepositHardshipRequestRecorder.record_request(
            self.member, self.member, {}
        )
        again = AssociationDepositHardshipRequestRecorder.record_request(
            self.member, self.member, {}
        )
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(first.hardship_requested_at, again.hardship_requested_at)
        self.assertIsNone(again.agreed_amount)
        self.assertIsNone(again.effective_from)
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(1, again.agreement_revision)
        self.assertEqual(1, AssociationDepositHardshipRequestedLogEntry.objects.count())

    def test_approved_four_rates_and_repeat_create_one_plan_and_consent_audit(self):
        key = uuid.uuid4()
        account = self.authorize(request_key=key, expected_revision=0)
        original = list(account.payments.order_by("pk").values())
        self.authorize(request_key=key, expected_revision=0)
        self.assertEqual(original, list(account.payments.order_by("pk").values()))
        self.assertEqual(
            [Decimal("50")] * 4, list(account.payments.values_list("amount", flat=True))
        )
        audit = AssociationDepositAgreementAuthorizedLogEntry.objects.get()
        self.assertEqual(self.admin.pk, audit.actor_id)
        self.assertIn("zugestimmt", audit.values["consent_note"])
        self.assertEqual("2026-11-05", audit.values["consented_on"])
        self.assertEqual(1, account.agreement_revision)
        with self.assertRaisesMessage(ValidationError, "Anfrageschlüssel"):
            self.authorize(request_key=key, expected_revision=0, amount=Decimal("250"))

    def test_hardship_waiver_is_explicit_zero_without_payment(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        AssociationDepositHardshipRequestRecorder.record_request(
            self.member, self.member, {}
        )
        account = self.authorize(amount=Decimal("0"), instalment_count=1)
        self.assertEqual(Decimal("0"), account.agreed_amount)
        self.assertEqual(self.today, account.effective_from)
        self.assertFalse(Payment.objects.exists())
        self.assertIsNotNone(account.hardship_requested_at)
        with self.assertRaisesMessage(ValidationError, "bereits"):
            AssociationDepositHardshipRequestRecorder.record_request(
                self.member, self.member, {}
            )

    def test_reduced_total_does_not_create_claim_for_difference_from_minimum(self):
        account = self.authorize(amount=Decimal("100"))
        self.assertEqual(Decimal("100"), account.agreed_amount)
        self.assertEqual(
            [Decimal("25")] * 4, list(account.payments.values_list("amount", flat=True))
        )

    def test_received_credit_is_preserved_and_only_actual_remainder_scheduled(self):
        AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("25"),
            self.today,
            "before-agreement",
            "Kontoauszug",
            self.admin,
            {},
        )
        account = self.authorize(amount=Decimal("75"), instalment_count=2)
        self.assertEqual(Decimal("25"), account.receipts.get().amount)
        self.assertEqual(
            [Decimal("25")] * 2, list(account.payments.values_list("amount", flat=True))
        )

    def test_paid_history_survives_reduction_and_subsequent_waiver(self):
        account = self.authorize(amount=Decimal("100"))
        paid = account.payments.order_by("due_date").first()
        paid.status = Payment.PaymentStatus.PAID
        paid.save()
        original = list(Payment.objects.filter(pk=paid.pk).values())
        self.authorize(amount=Decimal("75"), instalment_count=2)
        self.assertEqual(
            [Decimal("25")] * 2,
            list(
                account.payments.filter(
                    transaction=None, status=Payment.PaymentStatus.DUE
                ).values_list("amount", flat=True)
            ),
        )
        self.authorize(amount=Decimal("0"), instalment_count=1)
        self.assertEqual(original, list(account.payments.values()))
        self.assertEqual(
            3, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )

    def test_stale_admin_and_conflicting_repeat_leave_current_plan_unchanged(self):
        account = self.authorize()
        original = list(account.payments.order_by("pk").values())
        with self.assertRaisesMessage(ValidationError, "inzwischen"):
            self.authorize(amount=Decimal("75"), expected_revision=0)
        self.assertEqual(original, list(account.payments.order_by("pk").values()))
        self.assertEqual(
            1, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )

    def test_permission_consent_dates_and_cent_validation_fail_without_financial_writes(
        self,
    ):
        with self.assertRaises(PermissionDenied):
            self.authorize(actor=self.member)
        for changes in [
            dict(consent_note=" "),
            dict(consented_on=self.today + datetime.timedelta(days=1)),
            dict(effective_from=self.today - datetime.timedelta(days=1)),
            dict(amount=Decimal("100.001")),
            dict(instalment_count=0),
            dict(amount=Decimal("0.01"), instalment_count=2),
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.authorize(**changes)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_audit_failure_rolls_back_agreement_and_payments(self):
        with patch.object(
            AssociationDepositAgreementAuthorizedLogEntry,
            "save",
            side_effect=RuntimeError("Audit ausgefallen"),
        ):
            with self.assertRaises(RuntimeError):
                self.authorize()
        self.assertFalse(AssociationDepositAccount.objects.exists())
        self.assertFalse(Payment.objects.exists())

    def test_no_membership_cannot_create_or_export_positive_deposit(self):
        AssociationMembership.objects.filter(member=self.member).delete()
        with self.assertRaisesMessage(ValidationError, "Vereinsmitgliedschaft"):
            self.authorize()
        account = AssociationDepositAccountFactory(
            member=self.member, agreed_amount=200, effective_from=self.today
        )
        payment = PaymentFactory(
            association_deposit_account=account,
            mandate_ref=MandateReferenceFactory(member=self.member),
            amount=200,
            due_date=self.today,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
        )
        self.assertEqual(
            [],
            AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                self.today, {}
            ),
        )
        payment.refresh_from_db()
        self.assertIsNone(payment.transaction_id)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)

    def test_admin_requested_start_cannot_bypass_future_membership_or_trial_boundary(
        self,
    ):
        start = datetime.date(2026, 12, 12)
        AssociationMembership.objects.filter(member=self.member).update(
            start_date=start
        )
        account = self.authorize(effective_from=self.today)
        self.assertEqual(
            datetime.date(2027, 1, 5),
            account.payments.order_by("due_date").first().due_date,
        )
        self.assertEqual(
            [],
            AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                datetime.date(2026, 12, 5), {}
            ),
        )

    def test_effective_exit_holds_unexported_future_rates(self):
        account = self.authorize()
        AssociationMembership.objects.filter(member=self.member).update(
            end_date=datetime.date(2026, 11, 30)
        )
        original = list(account.payments.order_by("pk").values())
        self.assertEqual(
            [],
            AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                datetime.date(2026, 12, 5), {}
            ),
        )
        self.assertEqual(original, list(account.payments.order_by("pk").values()))

    def test_database_rejects_zero_instalments_on_insert_and_update(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssociationDepositAccount.objects.create(
                member=self.member, instalment_count=0
            )
        account = AssociationDepositAccount.objects.create(member=self.member)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssociationDepositAccount.objects.filter(pk=account.pk).update(
                instalment_count=0
            )
        account.refresh_from_db()
        self.assertEqual(1, account.instalment_count)

    def test_monthly_calendar_restores_configured_due_day_after_clamped_month(self):
        cases = [
            (31, datetime.date(2027, 2, 1), ["2027-02-28", "2027-03-31", "2027-04-30"]),
            (31, datetime.date(2028, 2, 1), ["2028-02-29", "2028-03-31", "2028-04-30"]),
            (30, datetime.date(2027, 2, 1), ["2027-02-28", "2027-03-30", "2027-04-30"]),
            (30, datetime.date(2028, 2, 1), ["2028-02-29", "2028-03-30", "2028-04-30"]),
            (
                30,
                datetime.date(2027, 1, 31),
                ["2027-02-28", "2027-03-30", "2027-04-30"],
            ),
            (
                31,
                datetime.date(2027, 4, 30),
                ["2027-04-30", "2027-05-31", "2027-06-30"],
            ),
        ]
        for day, start, expected in cases:
            with self.subTest(day=day, start=start):
                self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, day)
                plan = AssociationDepositInstalmentCalculator.build_payment_schedule(
                    Decimal("200"), 3, start, {}
                )
                self.assertEqual(
                    expected, [rate["due_date"].isoformat() for rate in plan]
                )
                self.assertEqual(
                    [Decimal("66.67"), Decimal("66.67"), Decimal("66.66")],
                    [rate["amount"] for rate in plan],
                )
                self.assertEqual(Decimal("200"), sum(rate["amount"] for rate in plan))

    def test_member_increase_invalidates_an_older_admin_revision(self):
        account = AssociationDepositAgreementCreator.create_regular_agreement(
            self.member, Decimal("200"), self.today, self.member, {}
        )
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            self.member, self.member, {}
        )
        old_revision = account.agreement_revision
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        self.assertFalse(account.is_individual_agreement)
        self.assertTrue(
            AssociationDepositDetailsProvider.get_deposit_details(self.member, {})[
                "can_increase"
            ]
        )
        AssociationDepositIncreaseRecorder.increase_agreed_deposit(
            self.member, Decimal("250"), self.member, {}
        )
        with self.assertRaisesMessage(ValidationError, "inzwischen"):
            self.authorize(amount=Decimal("75"), expected_revision=old_revision)
        account.refresh_from_db()
        self.assertEqual(Decimal("250"), account.agreed_amount)
        self.assertEqual(Decimal("250"), account.payments.get().amount)

    def test_individual_single_and_multi_rate_agreements_forbid_member_increases(self):
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        for count in [1, 4]:
            with self.subTest(count=count):
                account = self.authorize(amount=Decimal("100"), instalment_count=count)
                self.assertTrue(account.is_individual_agreement)
                self.assertFalse(
                    AssociationDepositDetailsProvider.get_deposit_details(
                        self.member, {}
                    )["can_increase"]
                )
                before = list(account.payments.order_by("pk").values())
                with self.assertRaisesMessage(
                    ValidationError, "Verwaltungsvereinbarung"
                ):
                    AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                        self.member, Decimal("250"), self.member, {}
                    )
                self.assertEqual(before, list(account.payments.order_by("pk").values()))
                with self.assertRaisesMessage(ValidationError, "abweichende"):
                    AssociationDepositAgreementCreator.create_regular_agreement(
                        self.member,
                        Decimal("100"),
                        self.today,
                        self.member,
                        {},
                    )

    def test_old_request_retry_never_overwrites_a_newer_agreement_even_next_day(self):
        key = uuid.uuid4()
        self.authorize(request_key=key, expected_revision=0)
        self.authorize(amount=Decimal("100"), instalment_count=2)
        before = list(Payment.objects.order_by("pk").values())
        mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        self.authorize(request_key=key, expected_revision=0)
        self.assertEqual(before, list(Payment.objects.order_by("pk").values()))
        self.assertEqual(
            2, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )

    def test_pending_hardship_cannot_become_regular_debt_without_authorization(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, True)
        AssociationDepositHardshipRequestRecorder.record_request(
            self.member, self.member, {}
        )
        with self.assertRaisesMessage(ValidationError, "individuelle"):
            AssociationDepositAgreementCreator.create_regular_agreement(
                self.member, Decimal("200"), self.today, self.member, {}
            )
        self.assertFalse(Payment.objects.exists())
        self.assertIsNone(AssociationDepositAccount.objects.get().agreed_amount)

    def test_failed_plan_change_preserves_existing_rates_and_agreement(self):
        account = self.authorize()
        before = list(account.payments.order_by("pk").values())
        with patch.object(
            AssociationDepositAgreementAuthorizedLogEntry,
            "save",
            side_effect=RuntimeError("Audit ausgefallen"),
        ):
            with self.assertRaises(RuntimeError):
                self.authorize(amount=Decimal("75"), instalment_count=2)
        account.refresh_from_db()
        self.assertEqual(Decimal("200"), account.agreed_amount)
        self.assertEqual(1, account.agreement_revision)
        self.assertEqual(before, list(account.payments.order_by("pk").values()))
        self.assertEqual(
            1, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )

    def test_unagreed_and_waived_accounts_are_held_even_with_manual_due_rows(self):
        account = AssociationDepositAccountFactory(member=self.member)
        payment = PaymentFactory(
            association_deposit_account=account,
            mandate_ref=MandateReferenceFactory(member=self.member),
            amount=200,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            due_date=self.today,
        )
        self.assertEqual(
            [],
            AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                self.today, {}
            ),
        )
        account.agreed_amount = 0
        account.effective_from = self.today
        account.save()
        self.assertEqual(
            [],
            AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                self.today, {}
            ),
        )
        payment.refresh_from_db()
        self.assertEqual(Decimal("200"), payment.amount)
        self.assertIsNone(payment.transaction_id)
