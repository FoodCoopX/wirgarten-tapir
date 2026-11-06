import datetime
import uuid
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.urls import reverse

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositRefund,
    AssociationDepositRefundCreatedLogEntry,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_agreement_creator import (
    AssociationDepositAgreementCreator,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_deposit_refund_recorder import (
    AssociationDepositRefundRecorder,
)
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.tests.factories import (
    AssociationDepositAccountFactory,
    AssociationMembershipFactory,
)
from tapir.associations.services.association_deposit_administration_provider import (
    AssociationDepositAdministrationProvider,
)
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.payments.services.subscription_payments_rebuilder import (
    SubscriptionPaymentsRebuilder,
)
from tapir.wirgarten.models import ExportedFile, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositRefunds(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.today = datetime.date(2026, 11, 6)
        mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        for key, value in {
            ParameterKeys.ORGANISATION_LEGAL_STATUS: LEGAL_STATUS_ASSOCIATION,
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED: True,
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE: True,
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED: True,
            ParameterKeys.PAYMENT_DUE_DAY: 5,
            ParameterKeys.PAYMENT_START_DATE: self.today,
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "NL88ABNA2011060885",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "DE98ZZZ09999999999",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
        }.items():
            self._set_parameter(key, value)
        self.member = MemberFactory(
            iban="NL88ABNA2011060885", account_owner="Test Mitglied"
        )
        self.admin = MemberFactory(is_superuser=True)
        self.membership = AssociationMembershipFactory(
            member=self.member, start_date=self.today
        )
        AssociationDepositSignupHandler.create_signup_deposit(
            self.member,
            Decimal("200"),
            self.today,
            True,
            self.member,
            {},
            payment_option="standard_instalments",
            expected_instalments=4,
        )
        self.account = AssociationDepositAccount.objects.get(member=self.member)

    def cash(self, amount="200", reference="external-receipt"):
        return AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal(amount),
            self.today,
            reference,
            "Kontoauszug",
            self.admin,
            {},
        )

    def refund_data(self, amount="50", reference="external-refund"):
        self.account.refresh_from_db()
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        return dict(
            member=self.member,
            amount=Decimal(amount),
            refunded_on=self.today,
            reference=reference,
            note="Ausgeführte Rückzahlung laut Kontoauszug",
            bank_settlement_confirmed=True,
            expected_revision=self.account.agreement_revision,
            expected_committed_amount=details["committed_amount"],
            actor=self.admin,
            cache={},
        )

    def agreement_data(self, amount="200"):
        self.account.refresh_from_db()
        return dict(
            member=self.member,
            amount=Decimal(amount),
            effective_from=self.today,
            instalment_count=4,
            consented_on=self.today,
            consent_note="Neue persönliche Zustimmung",
            expected_revision=self.account.agreement_revision,
            request_key=uuid.uuid4(),
            actor=self.admin,
            cache={},
        )

    def test_partial_refund_holds_existing_rates_without_inflation_through_receipts_and_rebuilds(
        self,
    ):
        self.cash("100")
        before = list(self.account.payments.order_by("pk").values())
        self.assertEqual(
            [Decimal("50"), Decimal("50")], [row["amount"] for row in before]
        )
        AssociationDepositRefundRecorder.record_external_refund(
            **self.refund_data("25")
        )
        self.cash("25", "later-receipt")
        for operation in [
            lambda: AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
                self.member, self.admin, {}
            ),
            lambda: AssociationDepositPaymentSynchronizer.update_existing_deposit_payment(
                self.member, {}
            ),
            lambda: SubscriptionPaymentsRebuilder.rebuild_subscription_payments(
                self.today.replace(day=1), {}
            ),
            lambda: call_command("rebuild_payment_history", no_confirm=True),
        ]:
            operation()
            self.assertEqual(
                before, list(self.account.payments.order_by("pk").values())
            )
        PaymentExportBuilder.export_association_deposit_payments(
            datetime.date(2027, 3, 5), False, {}
        )
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(
            (125, 0, 25, 100),
            tuple(
                details[key]
                for key in [
                    "received_amount",
                    "committed_amount",
                    "refunded_amount",
                    "retained_amount",
                ]
            ),
        )
        self.assertEqual(
            (0, 100), (details["pending_amount"], details["stopped_amount"])
        )
        self.assertFalse(details["can_increase"])

    def test_full_refund_then_reentry_and_new_consent_use_net_not_gross_receipts(self):
        receipt = self.cash()
        original_receipt = dict(self.account.receipts.values().get())
        AssociationDepositRefundRecorder.record_external_refund(
            **self.refund_data("200")
        )
        AssociationMembershipChangeHandler.set_end_date(
            self.membership, self.today, self.admin, {}
        )
        AssociationMembershipChangeHandler.start_membership(
            self.member, self.membership.type, datetime.date(2027, 3, 1), self.admin, {}
        )
        self.assertFalse(self.account.payments.exists())
        data = self.agreement_data()
        data["effective_from"] = datetime.date(2027, 3, 1)
        AssociationDepositAgreementAuthorizer.authorize_agreement(**data)
        self.assertEqual(
            [Decimal("50")] * 4,
            list(
                self.account.payments.order_by("due_date").values_list(
                    "amount", flat=True
                )
            ),
        )
        self.assertEqual(
            original_receipt,
            dict(self.account.receipts.filter(pk=receipt.pk).values().get()),
        )
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(
            (200, 200, 0, 200),
            tuple(
                details[key]
                for key in [
                    "received_amount",
                    "refunded_amount",
                    "retained_amount",
                    "pending_amount",
                ]
            ),
        )

    def test_partial_50_refund_then_new_200_agreement_collects_only_50(self):
        self.cash()
        AssociationDepositRefundRecorder.record_external_refund(
            **self.refund_data("50")
        )
        self.assertFalse(self.account.payments.exists())
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            **self.agreement_data("200")
        )
        self.assertEqual(
            [Decimal("12.50")] * 4,
            list(
                self.account.payments.order_by("due_date").values_list(
                    "amount", flat=True
                )
            ),
        )
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(
            (150, 50), (details["retained_amount"], details["pending_amount"])
        )

    def test_full_refund_of_booked_sepa_preserves_paid_rows_files_and_new_plan(self):
        self.assertEqual(
            [],
            PaymentExportBuilder.export_association_deposit_payments(
                datetime.date(2027, 3, 5), False, {}
            ),
        )
        before = list(self.account.payments.order_by("pk").values())
        files = list(ExportedFile.objects.order_by("pk").values())
        self.assertEqual(4, len(before))
        self.today = datetime.date(2027, 3, 6)
        mock_timezone(self, datetime.datetime(2027, 3, 6, 12))
        AssociationDepositRefundRecorder.record_external_refund(
            **self.refund_data("200")
        )
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(
            (0, 200, 200, 0),
            tuple(
                details[key]
                for key in [
                    "received_amount",
                    "committed_amount",
                    "refunded_amount",
                    "retained_amount",
                ]
            ),
        )
        self.assertIsNone(
            AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
                self.member, self.admin, {}
            )
        )
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            **self.agreement_data()
        )
        self.assertEqual(
            [Decimal("50")] * 4,
            list(
                self.account.payments.filter(status=Payment.PaymentStatus.DUE)
                .order_by("due_date")
                .values_list("amount", flat=True)
            ),
        )
        self.assertEqual(
            before,
            list(
                self.account.payments.filter(pk__in=[row["id"] for row in before])
                .order_by("pk")
                .values()
            ),
        )
        self.assertEqual(files, list(ExportedFile.objects.order_by("pk").values()))

    def test_only_new_financial_consent_clears_hold_not_membership_changes_or_old_request(
        self,
    ):
        self.cash()
        old_agreement = self.agreement_data()
        AssociationDepositAgreementAuthorizer.authorize_agreement(**old_agreement)
        refund_request = self.refund_data()
        refund = AssociationDepositRefundRecorder.record_external_refund(
            **refund_request
        )
        AssociationMembershipChangeHandler.set_end_date(
            self.membership, datetime.date(2026, 12, 31), self.admin, {}
        )
        AssociationMembershipChangeHandler.set_end_date(
            self.membership, None, self.admin, {}
        )
        AssociationMembershipChangeHandler.start_membership(
            self.member, self.membership.type, self.today, self.admin, {}
        )
        AssociationDepositAgreementAuthorizer.authorize_agreement(**old_agreement)
        self.account.refresh_from_db()
        self.assertTrue(self.account.refund_requires_agreement)
        self.assertFalse(self.account.payments.exists())
        with self.assertRaisesMessage(ValidationError, "dokumentierte"):
            AssociationDepositAgreementCreator.create_regular_agreement(
                self.member,
                Decimal("200"),
                self.today,
                self.member,
                {},
                instalment_count=4,
            )
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            **self.agreement_data("150")
        )
        self.account.refresh_from_db()
        revision = self.account.agreement_revision
        self.assertFalse(self.account.refund_requires_agreement)
        self.assertEqual(
            refund.pk,
            AssociationDepositRefundRecorder.record_external_refund(
                **refund_request
            ).pk,
        )
        self.account.refresh_from_db()
        self.assertFalse(self.account.refund_requires_agreement)
        self.assertEqual(revision, self.account.agreement_revision)
        self.assertEqual(1, AssociationDepositRefundCreatedLogEntry.objects.count())
        self.assertFalse(self.account.payments.exists())

    def test_invalid_or_conflicting_refunds_do_not_write(self):
        self.cash()
        for values in [
            dict(amount=Decimal("0")),
            dict(amount=Decimal("-1")),
            dict(amount=Decimal("0.001")),
            dict(amount=Decimal("201")),
            dict(refunded_on=self.today + datetime.timedelta(days=1)),
            dict(reference=""),
            dict(note=""),
            dict(bank_settlement_confirmed=False),
        ]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                AssociationDepositRefundRecorder.record_external_refund(
                    **(self.refund_data() | values)
                )
        self.assertFalse(AssociationDepositRefund.objects.exists())
        request = self.refund_data()
        AssociationDepositRefundRecorder.record_external_refund(**request)
        for values in [
            dict(amount=Decimal("25")),
            dict(note="Anderer Beleg"),
            dict(refunded_on=self.today - datetime.timedelta(days=1)),
        ]:
            with self.subTest(values=values), self.assertRaisesMessage(
                ValidationError, "anderen Daten"
            ):
                AssociationDepositRefundRecorder.record_external_refund(
                    **(request | values)
                )
        self.assertEqual(1, AssociationDepositRefund.objects.count())

    def test_scheduled_due_amount_is_not_refundable_money_and_permission_is_required(
        self,
    ):
        with self.assertRaisesMessage(ValidationError, "Buchungsrest"):
            AssociationDepositRefundRecorder.record_external_refund(
                **self.refund_data("1")
            )
        self.cash()
        with self.assertRaises(PermissionDenied):
            AssociationDepositRefundRecorder.record_external_refund(
                **(self.refund_data() | dict(actor=self.member))
            )
        self.assertFalse(AssociationDepositRefund.objects.exists())

    def test_unknown_and_zero_remain_distinct_after_actual_refund(self):
        for amount in [None, Decimal("0")]:
            with self.subTest(amount=amount):
                member = MemberFactory()
                AssociationMembershipFactory(member=member, start_date=self.today)
                if amount == 0:
                    AssociationDepositAgreementAuthorizer.authorize_agreement(
                        member,
                        amount,
                        self.today,
                        1,
                        self.today,
                        "Dokumentierter Verzicht",
                        0,
                        uuid.uuid4(),
                        self.admin,
                        {},
                    )
                AssociationDepositReceiptRecorder.record_received_deposit(
                    member,
                    Decimal("25"),
                    self.today,
                    f"incoming-{amount}",
                    "Kontoauszug",
                    self.admin,
                    {},
                )
                account = AssociationDepositAccount.objects.get(member=member)
                AssociationDepositRefundRecorder.record_external_refund(
                    member,
                    Decimal("25"),
                    self.today,
                    f"refund-{amount}",
                    "Bankbeleg",
                    True,
                    account.agreement_revision,
                    Decimal("0"),
                    self.admin,
                    {},
                )
                details = AssociationDepositDetailsProvider.get_deposit_details(
                    member, {}
                )
                self.assertEqual(amount, details["agreed_amount"])
                self.assertEqual(
                    "waived" if amount == 0 else "not_agreed", details["state"]
                )
                self.assertIsNone(account.hardship_requested_at)
                self.assertFalse(account.payments.exists())
                self.assertEqual(0, details["retained_amount"])

    def test_stale_form_requires_reconfirmation_but_identical_refund_replay_is_safe(
        self,
    ):
        self.cash()
        request = self.refund_data()
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            **self.agreement_data("150")
        )
        with self.assertRaisesMessage(ValidationError, "inzwischen"):
            AssociationDepositRefundRecorder.record_external_refund(**request)
        self.assertFalse(AssociationDepositRefund.objects.exists())

    def test_departed_fully_refunded_case_is_history_but_return_needs_followup(self):
        member = MemberFactory()
        start = self.today - datetime.timedelta(days=30)
        end = self.today - datetime.timedelta(days=1)
        membership = AssociationMembershipFactory(
            member=member, start_date=start, end_date=end
        )
        account = AssociationDepositAccountFactory(
            member=member, agreed_amount=200, effective_from=start
        )
        AssociationDepositReceiptRecorder.record_received_deposit(
            member, Decimal("200"), end, "departed-cash", "Kontoauszug", self.admin, {}
        )
        AssociationDepositRefundRecorder.record_external_refund(
            member,
            Decimal("200"),
            self.today,
            "departed-refund",
            "Ausgeführte Rückzahlung",
            True,
            account.agreement_revision,
            Decimal("0"),
            self.admin,
            {},
        )
        self.assertNotIn(
            account, AssociationDepositAdministrationProvider.get_accounts(False, {})
        )
        self.assertIn(
            account, AssociationDepositAdministrationProvider.get_accounts(True, {})
        )
        future = AssociationMembershipChangeHandler.start_membership(
            member, membership.type, datetime.date(2027, 3, 1), self.admin, {}
        )
        self.assertIn(
            account, AssociationDepositAdministrationProvider.get_accounts(False, {})
        )
        AssociationMembershipChangeHandler.set_end_date(
            future, datetime.date(2027, 3, 31), self.admin, {}
        )
        mock_timezone(self, datetime.datetime(2027, 4, 1, 12))
        self.assertNotIn(
            account, AssociationDepositAdministrationProvider.get_accounts(False, {})
        )
        self.assertIn(
            account, AssociationDepositAdministrationProvider.get_accounts(True, {})
        )
        AssociationMembershipChangeHandler.start_membership(
            member, membership.type, datetime.date(2027, 4, 1), self.admin, {}
        )
        self.assertIn(
            account, AssociationDepositAdministrationProvider.get_accounts(False, {})
        )
        account.refresh_from_db()
        self.assertTrue(account.refund_requires_agreement)
        self.assertFalse(account.payments.exists())
