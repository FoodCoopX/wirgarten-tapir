import datetime
import time
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositIncreasedLogEntry,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
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
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import MandateReference, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositIncreasePreview(TapirIntegrationTest):
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

    def test_preview_is_read_only_and_confirmation_preserves_existing_dates_and_ids(
        self,
    ):
        before = list(self.account.payments.order_by("pk").values())
        preview = self.preview()
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        self.assertEqual(
            [Decimal("62.50")] * 4, [p["amount"] for p in preview["payments"]]
        )
        self.confirm(preview)
        after = list(
            self.account.payments.order_by("due_date").values(
                "id", "amount", "due_date", "instalment_number"
            )
        )
        self.assertEqual(preview["payments"], after)
        self.assertEqual(1, AssociationDepositIncreasedLogEntry.objects.count())
        self.confirm(preview)
        self.assertEqual(
            after,
            list(
                self.account.payments.order_by("due_date").values(
                    "id", "amount", "due_date", "instalment_number"
                )
            ),
        )
        self.assertEqual(1, AssociationDepositIncreasedLogEntry.objects.count())

    def test_preexisting_receipt_credit_is_retained_in_standard_increase(self):
        self.receipt()
        preview = self.preview()
        self.assertEqual(
            [Decimal("37.50"), Decimal("62.50"), Decimal("62.50"), Decimal("62.50")],
            [p["amount"] for p in preview["payments"]],
        )
        self.assertEqual(Decimal("225"), preview["pending_amount"])
        self.confirm(preview)
        self.assertEqual(
            Decimal("225"), sum(self.account.payments.values_list("amount", flat=True))
        )

    def test_committed_history_is_preserved_and_remaining_rate_cents_sum_exactly(self):
        first = self.account.payments.order_by("due_date").first()
        first.status = Payment.PaymentStatus.PAID
        first.save()
        before = list(Payment.objects.filter(pk=first.pk).values())
        preview = self.preview()
        self.assertEqual(
            [Decimal("66.67"), Decimal("66.67"), Decimal("66.66")],
            [p["amount"] for p in preview["payments"]],
        )
        self.confirm(preview)
        self.assertEqual(before, list(Payment.objects.filter(pk=first.pk).values()))
        self.assertEqual(
            Decimal("250"), sum(self.account.payments.values_list("amount", flat=True))
        )

    def test_all_paid_plan_creates_only_confirmed_difference_with_shared_due_dates(
        self,
    ):
        self.account.payments.update(status=Payment.PaymentStatus.PAID)
        before = list(self.account.payments.order_by("pk").values())
        preview = self.preview()
        self.assertEqual(
            [Decimal("12.50")] * 4, [p["amount"] for p in preview["payments"]]
        )
        self.confirm(preview)
        pending = list(
            self.account.payments.filter(status=Payment.PaymentStatus.DUE)
            .order_by("due_date")
            .values("amount", "due_date", "instalment_number")
        )
        self.assertEqual(preview["payments"], pending)
        self.assertEqual(
            before,
            list(
                self.account.payments.filter(status=Payment.PaymentStatus.PAID)
                .order_by("pk")
                .values()
            ),
        )

    def test_receipt_after_preview_requires_new_confirmation_without_overwriting_it(
        self,
    ):
        preview = self.preview()
        self.receipt()
        before = list(self.account.payments.order_by("pk").values())
        with self.assertRaisesMessage(ValidationError, "Zahlungsstand"):
            self.confirm(preview)
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        self.account.refresh_from_db()
        self.assertEqual(Decimal("200"), self.account.agreed_amount)
        self.confirm(self.preview())
        self.assertEqual(
            Decimal("225"), sum(self.account.payments.values_list("amount", flat=True))
        )

    def test_export_after_preview_requires_new_confirmation_and_preserves_export(self):
        preview = self.preview()
        PaymentExportBuilder.export_all_unexported_payments(self.today, False, {})
        before = list(self.account.payments.order_by("pk").values())
        with self.assertRaisesMessage(ValidationError, "Zahlungsstand"):
            self.confirm(preview)
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))
        self.confirm(self.preview())
        self.assertEqual(
            Decimal("250"), sum(self.account.payments.values_list("amount", flat=True))
        )

    def test_standard_plan_uses_stored_count_and_both_organisation_permissions(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, "6")
        self.assertTrue(
            AssociationDepositDetailsProvider.get_deposit_details(self.member, {})[
                "can_increase"
            ]
        )
        self.assertEqual(4, len(self.preview()["payments"]))
        for key in [
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE,
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED,
        ]:
            with self.subTest(key=key):
                self._set_parameter(key, False)
                self.assertFalse(
                    AssociationDepositDetailsProvider.get_deposit_details(
                        self.member, {}
                    )["can_increase"]
                )
                with self.assertRaises(ValidationError):
                    self.preview()
                self._set_parameter(key, True)
        with self.assertRaisesMessage(ValidationError, "bestätigen"):
            AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                self.member, Decimal("250"), self.member, {}
            )

    def test_individual_single_or_multi_rate_terms_cannot_be_previewed_or_changed(self):
        for count in [1, 4]:
            with self.subTest(count=count):
                self.account.refresh_from_db()
                AssociationDepositAgreementAuthorizer.authorize_agreement(
                    self.member,
                    Decimal("100"),
                    self.today,
                    count,
                    self.today,
                    "Zugestimmt",
                    self.account.agreement_revision,
                    uuid.uuid4(),
                    self.admin,
                    {},
                )
                self.assertFalse(
                    AssociationDepositDetailsProvider.get_deposit_details(
                        self.member, {}
                    )["can_increase"]
                )
                with self.assertRaisesMessage(
                    ValidationError, "Verwaltungsvereinbarung"
                ):
                    self.preview()

    def test_tampered_expired_or_other_amount_confirmation_cannot_change_plan(self):
        preview = self.preview()
        with self.assertRaises(ValidationError):
            self.confirm({"confirmation": preview["confirmation"] + "x"})
        with self.assertRaises(ValidationError):
            self.confirm(preview, "300")
        future = time.time() + 901
        with patch("django.core.signing.time.time", return_value=future):
            with self.assertRaisesMessage(ValidationError, "nicht mehr gültig"):
                self.confirm(preview)
        self.account.refresh_from_db()
        self.assertEqual(Decimal("200"), self.account.agreed_amount)
        self.assertEqual(
            [Decimal("50")] * 4,
            list(self.account.payments.values_list("amount", flat=True)),
        )

    def test_preview_does_not_create_mandate_for_fully_received_historical_balance(
        self,
    ):
        self.account.payments.all().delete()
        MandateReference.objects.filter(member=self.member).delete()
        AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("200"),
            self.today,
            "historical-paid",
            "Kontoauszug",
            self.admin,
            {},
        )
        before = list(
            AssociationDepositAccount.objects.filter(pk=self.account.pk).values()
        )
        preview = self.preview()
        self.assertEqual(Decimal("50"), preview["pending_amount"])
        self.assertFalse(MandateReference.objects.filter(member=self.member).exists())
        self.assertFalse(self.account.payments.exists())
        self.assertEqual(
            before,
            list(AssociationDepositAccount.objects.filter(pk=self.account.pk).values()),
        )
