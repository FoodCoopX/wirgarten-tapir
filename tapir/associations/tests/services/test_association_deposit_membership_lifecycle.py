import datetime
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositMembershipChangedLogEntry,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_administration_provider import (
    AssociationDepositAdministrationProvider,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.tests.factories import (
    AssociationDepositAccountFactory,
    AssociationMembershipFactory,
)
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import ExportedFile, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.services.association_deposit_increase_preview import (
    AssociationDepositIncreasePreview,
)
from tapir.associations.services.association_deposit_increase_recorder import (
    AssociationDepositIncreaseRecorder,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)


class TestAssociationDepositMembershipLifecycle(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.today = datetime.date(2026, 11, 5)
        for key, value in {
            ParameterKeys.ORGANISATION_LEGAL_STATUS: LEGAL_STATUS_ASSOCIATION,
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED: True,
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE: True,
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED: True,
            ParameterKeys.PAYMENT_DUE_DAY: 5,
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "NL88ABNA2011060885",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "DE98ZZZ09999999999",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
        }.items():
            self._set_parameter(key, value)
        self.member = MemberFactory(
            iban="NL88ABNA2011060885", account_owner="Test Mitglied"
        )
        self.admin = MemberFactory(is_superuser=True)
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
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

    def preview(self, amount="250"):
        return AssociationDepositIncreasePreview.build_preview(
            self.member, Decimal(amount), {}
        )

    def confirm(self, preview, amount="250"):
        return AssociationDepositIncreaseRecorder.increase_agreed_deposit(
            self.member,
            Decimal(amount),
            self.member,
            {},
            confirmation=preview["confirmation"],
        )

    def receipt(self):
        return AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("25"),
            self.today,
            "preview-receipt",
            "Kontoauszug",
            self.admin,
            {},
        )

    def membership(self):
        return AssociationMembership.objects.get(member=self.member)

    def cancel(self, end=datetime.date(2026, 12, 31)):
        AssociationMembershipCancellationManager.cancel_association_membership(
            self.member, end, self.admin, {}
        )
        self.account.refresh_from_db()

    def rejoin(self, start=datetime.date(2027, 3, 1)):
        return AssociationMembershipChangeHandler.start_membership(
            self.member, self.membership().type, start, self.admin, {}
        )

    def details(self):
        return AssociationDepositDetailsProvider.get_deposit_details(self.member, {})

    def test_exit_preserves_four_rates_and_only_collects_covered_two(self):
        before = list(self.account.payments.order_by("pk").values())
        self.cancel()
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        self.assertEqual(200, self.account.agreed_amount)
        self.assertEqual(4, self.account.instalment_count)
        self.assertEqual(100, self.details()["pending_amount"])
        self.assertEqual(100, self.details()["stopped_amount"])
        self.assertEqual(
            [],
            PaymentExportBuilder.export_association_deposit_payments(
                datetime.date(2026, 12, 5), False, {}
            ),
        )
        self.assertEqual(
            [Decimal("50"), Decimal("50")],
            list(
                self.account.payments.filter(transaction__isnull=False)
                .order_by("due_date")
                .values_list("amount", flat=True)
            ),
        )
        self.assertEqual(0, self.details()["pending_amount"])
        self.assertEqual(100, self.details()["stopped_amount"])

    def test_gap_reentry_preserves_credit_and_requires_explicit_new_terms(self):
        self.receipt()
        old_rates = list(self.account.payments.order_by("pk").values())
        self.cancel()
        self.rejoin()
        self.account.refresh_from_db()
        self.assertEqual(200, self.account.agreed_amount)
        self.assertIsNone(self.account.hardship_requested_at)
        self.assertEqual("agreement_required", self.details()["state"])
        self.assertEqual(25, self.details()["received_amount"])
        self.assertFalse(self.details()["can_increase"])
        self.assertIn(
            self.account,
            AssociationDepositAdministrationProvider.get_accounts(False, {}),
        )
        PaymentExportBuilder.export_association_deposit_payments(
            datetime.date(2027, 3, 5), False, {}
        )
        self.assertEqual(old_rates, list(self.account.payments.order_by("pk").values()))
        self.assertFalse(
            self.account.payments.filter(transaction__isnull=False).exists()
        )
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            self.member,
            Decimal("100"),
            datetime.date(2027, 1, 1),
            4,
            self.today,
            "Neue persönliche Zustimmung",
            self.account.agreement_revision,
            uuid.uuid4(),
            self.admin,
            {},
        )
        self.assertEqual(
            [Decimal("18.75")] * 4,
            list(
                self.account.payments.order_by("due_date").values_list(
                    "amount", flat=True
                )
            ),
        )
        self.assertEqual(25, self.details()["received_amount"])
        self.assertEqual("individual", self.details()["state"])
        self.assertEqual(
            datetime.date(2027, 3, 5),
            self.account.payments.order_by("due_date").first().due_date,
        )
        self.account.refresh_from_db()
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            self.member,
            Decimal("0"),
            datetime.date(2027, 1, 1),
            1,
            self.today,
            "Vollständiger Verzicht persönlich vereinbart",
            self.account.agreement_revision,
            uuid.uuid4(),
            self.admin,
            {},
        )
        self.assertFalse(self.account.payments.exists())
        self.assertEqual("waived", self.details()["state"])
        self.assertEqual(25, self.details()["overpayment_credit"])

    def test_adjacent_type_change_keeps_schedule_and_invalidates_both_forms(self):
        preview = self.preview()
        before = list(self.account.payments.order_by("pk").values())
        self.cancel()
        self.rejoin(datetime.date(2027, 1, 1))
        self.account.refresh_from_db()
        self.assertIsNone(self.account.collection_stopped_from)
        self.assertEqual(200, self.details()["pending_amount"])
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        with self.assertRaises(ValidationError):
            self.confirm(preview)
        with self.assertRaisesMessage(ValidationError, "inzwischen"):
            AssociationDepositAgreementAuthorizer.authorize_agreement(
                self.member,
                Decimal("100"),
                self.today,
                4,
                self.today,
                "Veraltetes Formular",
                0,
                uuid.uuid4(),
                self.admin,
                {},
            )

    def test_one_uncovered_day_is_a_gap(self):
        self.cancel()
        self.rejoin(datetime.date(2027, 1, 2))
        self.assertEqual("agreement_required", self.details()["state"])
        self.assertEqual(100, self.details()["stopped_amount"])

    def test_same_day_type_change_preserves_schedule(self):
        before = list(self.account.payments.order_by("pk").values())
        self.rejoin(self.today)
        self.assertEqual("regular", self.details()["state"])
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        self.assertEqual(1, AssociationDepositMembershipChangedLogEntry.objects.count())

    def test_future_end_retraction_restores_existing_rates_before_gap(self):
        before = list(self.account.payments.order_by("pk").values())
        self.cancel()
        AssociationMembershipChangeHandler.set_end_date(
            self.membership(), None, self.admin, {}
        )
        self.assertEqual(200, self.details()["pending_amount"])
        self.assertEqual(0, self.details()["stopped_amount"])
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))

    def test_end_retraction_after_gap_never_revives_old_rates(self):
        self.cancel()
        mock_timezone(self, datetime.datetime(2027, 2, 1, 12))
        AssociationMembershipChangeHandler.set_end_date(
            self.membership(), None, self.admin, {}
        )
        self.assertEqual("agreement_required", self.details()["state"])
        self.assertEqual(0, self.details()["pending_amount"])
        self.assertEqual(200, self.details()["stopped_amount"])

    def test_direct_history_change_and_time_passage_cannot_export_old_overdue_rates(
        self,
    ):
        membership = self.membership()
        membership.end_date = datetime.date(2026, 12, 31)
        membership.save()
        AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2027, 3, 1)
        )
        mock_timezone(self, datetime.datetime(2027, 3, 1, 12))
        PaymentExportBuilder.export_association_deposit_payments(
            datetime.date(2027, 3, 5), False, {}
        )
        self.assertFalse(
            self.account.payments.filter(transaction__isnull=False).exists()
        )
        self.assertEqual(200, self.details()["stopped_amount"])

    def test_cancel_manager_deletes_future_membership_without_losing_cutoff(self):
        self.rejoin(datetime.date(2027, 1, 1))
        self.cancel()
        self.assertEqual(
            1, AssociationMembership.objects.filter(member=self.member).count()
        )
        self.assertEqual(100, self.details()["pending_amount"])
        self.assertEqual(100, self.details()["stopped_amount"])

    def test_no_account_membership_changes_never_backfill(self):
        member = MemberFactory()
        membership = AssociationMembershipFactory(member=member, start_date=self.today)
        AssociationMembershipChangeHandler.set_end_date(
            membership, self.today, self.admin, {}
        )
        AssociationMembershipChangeHandler.start_membership(
            member, membership.type, datetime.date(2027, 3, 1), self.admin, {}
        )
        self.assertFalse(
            AssociationDepositAccount.objects.filter(member=member).exists()
        )

    def test_direct_membership_type_edit_invalidates_signed_preview(self):
        preview = self.preview()
        membership = self.membership()
        membership.type = AssociationMembershipFactory().type
        membership.save()
        with self.assertRaisesMessage(ValidationError, "inzwischen"):
            self.confirm(preview)

    def test_four_rate_details_reuse_coverage_and_same_cache_edit_is_fresh(self):
        request_cache = {}
        with CaptureQueriesContext(connection) as queries:
            case = AssociationDepositAdministrationProvider.get_case(
                self.member, request_cache
            )
        membership_reads = [
            q
            for q in queries
            if 'FROM "associations_associationmembership"' in q["sql"]
        ]
        self.assertLessEqual(len(membership_reads), 3)
        self.assertEqual(4, len(case["payments"]))
        self.assertEqual(200, case["details"]["pending_amount"])
        AssociationMembershipChangeHandler.set_end_date(
            self.membership(), datetime.date(2026, 12, 31), self.admin, request_cache
        )
        with CaptureQueriesContext(connection) as queries:
            details = AssociationDepositDetailsProvider.get_deposit_details(
                self.member, request_cache
            )
        self.assertLessEqual(
            len(
                [
                    q
                    for q in queries
                    if 'FROM "associations_associationmembership"' in q["sql"]
                ]
            ),
            3,
        )
        self.assertEqual(Decimal("100"), details["pending_amount"])
        self.assertEqual(Decimal("100"), details["stopped_amount"])
        AssociationMembershipChangeHandler.start_membership(
            self.member,
            self.membership().type,
            datetime.date(2027, 1, 1),
            self.admin,
            request_cache,
        )
        details = AssociationDepositDetailsProvider.get_deposit_details(
            self.member, request_cache
        )
        self.assertEqual(200, details["pending_amount"])
        self.assertEqual(0, details["stopped_amount"])

    def test_future_payment_api_matches_card_after_exit_and_reentry(self):
        self.client.force_login(self.admin)
        self.cancel()
        url = reverse("payments:member_future_payments")
        response = self.client.get(url, {"member_id": self.member.pk})
        self.assertEqual(200, response.status_code)
        rows = [entry["payment"] for entry in response.json()["payments"]]
        deposit_ids = set(self.account.payments.values_list("pk", flat=True))
        deposits = [row for row in rows if row["id"] in deposit_ids]
        self.assertEqual(
            ["2026-11-05", "2026-12-05"], [row["due_date"] for row in deposits]
        )
        self.assertEqual(
            self.details()["pending_amount"], sum(row["amount"] for row in deposits)
        )
        self.rejoin()
        mock_timezone(self, datetime.datetime(2027, 3, 1, 12))
        self.client.force_login(self.admin)
        response = self.client.get(url, {"member_id": self.member.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(
            [
                entry
                for entry in response.json()["payments"]
                if entry["payment"]["id"] in deposit_ids
            ]
        )
        self.assertEqual(0, self.details()["pending_amount"])

    def test_upcoming_api_keeps_paid_rows_and_four_rate_filter_has_bounded_reads(self):
        paid = self.account.payments.order_by("due_date").last()
        paid.status = Payment.PaymentStatus.PAID
        paid.save()
        self.cancel()
        self.client.force_login(self.admin)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                reverse("payments:member_future_payments"),
                {"member_id": self.member.pk},
            )
        self.assertEqual(200, response.status_code)
        membership_reads = [
            q
            for q in queries
            if 'FROM "associations_associationmembership"' in q["sql"]
        ]
        self.assertLessEqual(len(membership_reads), 4)
        deposit_ids = set(self.account.payments.values_list("pk", flat=True))
        deposits = [
            row["payment"]
            for row in response.json()["payments"]
            if row["payment"]["id"] in deposit_ids
        ]
        self.assertEqual(3, len(deposits))
        self.assertIn(paid.pk, [row["id"] for row in deposits])

    def test_export_coverage_four_rates_has_bounded_member_queries(self):
        with CaptureQueriesContext(connection) as queries:
            payments = (
                AssociationDepositPaymentSynchronizer.prepare_due_payments_for_export(
                    datetime.date(2027, 2, 5), {}
                )
            )
        self.assertEqual(4, len(payments))
        member_reads = [q for q in queries if 'FROM "wirgarten_member"' in q["sql"]]
        self.assertLessEqual(len(member_reads), 4)

    def test_membership_edit_invalidates_bulk_maps_without_duplicating_other_member(
        self,
    ):
        other = AssociationMembershipFactory(start_date=self.today)
        request_cache = {}
        self.assertEqual(
            1,
            len(
                TapirCache.get_member_association_memberships(
                    request_cache, self.member
                )
            ),
        )
        self.assertEqual(
            1,
            len(
                TapirCache.get_member_association_memberships(
                    request_cache, other.member
                )
            ),
        )
        AssociationMembershipChangeHandler.set_end_date(
            self.membership(), datetime.date(2026, 12, 31), self.admin, request_cache
        )
        own = TapirCache.get_member_association_memberships(request_cache, self.member)
        others = TapirCache.get_member_association_memberships(
            request_cache, other.member
        )
        self.assertEqual(1, len(own))
        self.assertEqual(datetime.date(2026, 12, 31), own[0].end_date)
        self.assertEqual([other.pk], [membership.pk for membership in others])

    def test_cancel_before_first_membership_requires_new_consent_on_return(self):
        member = MemberFactory(iban="NL88ABNA2011060885", account_owner="Test Mitglied")
        start = datetime.date(2026, 11, 9)
        membership = AssociationMembershipFactory(member=member, start_date=start)
        AssociationDepositSignupHandler.create_signup_deposit(
            member,
            Decimal("200"),
            start,
            True,
            member,
            {},
            payment_option="standard_instalments",
            expected_instalments=4,
        )
        account = AssociationDepositAccount.objects.get(member=member)
        AssociationDepositReceiptRecorder.record_received_deposit(
            member,
            Decimal("25"),
            self.today,
            "prestart-receipt",
            "Kontoauszug",
            self.admin,
            {},
        )
        old_rates = list(account.payments.order_by("pk").values())
        old_receipts = list(account.receipts.values())
        request_cache = {}
        AssociationMembershipCancellationManager.cancel_association_membership(
            member,
            self.today,
            self.admin,
            request_cache,
        )
        self.assertFalse(AssociationMembership.objects.filter(member=member).exists())
        AssociationMembershipChangeHandler.start_membership(
            member,
            membership.type,
            datetime.date(2027, 3, 1),
            self.admin,
            request_cache,
        )
        PaymentExportBuilder.export_association_deposit_payments(
            datetime.date(2027, 3, 5),
            False,
            {},
        )
        self.assertFalse(account.payments.filter(transaction__isnull=False).exists())
        self.assertEqual(old_rates, list(account.payments.order_by("pk").values()))
        self.assertEqual(old_receipts, list(account.receipts.values()))
        account.refresh_from_db()
        self.assertEqual(self.today, account.collection_stopped_from)
        self.assertEqual(
            (Decimal("200"), start, 4),
            (account.agreed_amount, account.effective_from, account.instalment_count),
        )
        self.assertIsNone(account.hardship_requested_at)
        details = AssociationDepositDetailsProvider.get_deposit_details(
            member, request_cache
        )
        self.assertEqual("agreement_required", details["state"])
        self.assertEqual(0, details["pending_amount"])
        self.assertEqual(175, details["stopped_amount"])
        AssociationDepositAgreementAuthorizer.authorize_agreement(
            member,
            Decimal("100"),
            datetime.date(2027, 3, 1),
            4,
            self.today,
            "Neue Zustimmung nach abgebrochenem Eintritt",
            account.agreement_revision,
            uuid.uuid4(),
            self.admin,
            request_cache,
        )
        self.assertEqual(
            [Decimal("18.75")] * 4,
            list(
                account.payments.order_by("due_date").values_list("amount", flat=True)
            ),
        )
        self.assertEqual(
            datetime.date(2027, 3, 5),
            account.payments.order_by("due_date").first().due_date,
        )
        self.assertEqual(old_receipts, list(account.receipts.values()))

    def test_prestart_cancellation_preserves_unknown_and_zero_terms(self):
        for amount in [None, Decimal("0")]:
            with self.subTest(amount=amount):
                member = MemberFactory()
                start = datetime.date(2026, 11, 9)
                membership = AssociationMembershipFactory(
                    member=member, start_date=start
                )
                account = AssociationDepositAccountFactory(
                    member=member,
                    agreed_amount=amount,
                    effective_from=start if amount is not None else None,
                )
                AssociationMembershipCancellationManager.cancel_association_membership(
                    member, self.today, self.admin, {}
                )
                AssociationMembershipChangeHandler.start_membership(
                    member, membership.type, datetime.date(2027, 3, 1), self.admin, {}
                )
                account.refresh_from_db()
                self.assertEqual(self.today, account.collection_stopped_from)
                self.assertEqual(amount, account.agreed_amount)
                self.assertEqual(
                    start if amount is not None else None, account.effective_from
                )
                self.assertIsNone(account.hardship_requested_at)
                self.assertFalse(account.payments.exists())
                details = AssociationDepositDetailsProvider.get_deposit_details(
                    member, {}
                )
                self.assertEqual("agreement_required", details["state"])
                self.assertEqual(amount, details["agreed_amount"])
                self.assertEqual(
                    None if amount is None else 0, details["overpayment_credit"]
                )
