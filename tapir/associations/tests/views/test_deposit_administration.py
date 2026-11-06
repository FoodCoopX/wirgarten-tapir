import datetime
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementAuthorizedLogEntry,
)
from tapir.associations.services.association_deposit_hardship_request_recorder import (
    AssociationDepositHardshipRequestRecorder,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Payment, ExportedFile
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestDepositAdministration(TapirIntegrationTest):
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
            ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED: True,
            ParameterKeys.SITE_ADMIN_EMAIL: "",
            ParameterKeys.PAYMENT_DUE_DAY: 5,
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "NL88ABNA2011060885",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "DE98ZZZ09999999999",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
        }.items():
            self._set_parameter(key, value)
        self.admin = MemberFactory(is_superuser=True)
        self.member = MemberFactory(
            iban="NL88ABNA2011060885", account_owner="Test Mitglied"
        )
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
        )
        self.client.force_login(self.admin)
        self.case_url = reverse(
            "associations:deposit_case", kwargs={"member_id": self.member.pk}
        )
        self.overview_url = reverse("associations:deposit_administration")

    def agreement_data(self, amount="200", count=4, revision=None, key=None):
        account = AssociationDepositAccount.objects.filter(member=self.member).first()
        return {
            "action": "agreement",
            "agreement-amount": amount,
            "agreement-effective_from": self.today.isoformat(),
            "agreement-instalment_count": count,
            "agreement-consented_on": self.today.isoformat(),
            "agreement-consent_note": "Persönliches Gespräch, Zustimmung dokumentiert",
            "agreement-expected_revision": (
                revision
                if revision is not None
                else (account.agreement_revision if account else 0)
            ),
            "agreement-request_key": str(key or uuid.uuid4()),
        }

    def receipt_data(self, committed="0", reference="bank-1", amount="25"):
        return {
            "action": "receipt",
            "receipt-amount": amount,
            "receipt-received_on": self.today.isoformat(),
            "receipt-reference": reference,
            "receipt-note": "Kontoauszug",
            "receipt-expected_committed_amount": committed,
        }

    def test_financial_permission_is_required_for_both_forms_and_overview(self):
        self.client.force_login(self.member)
        for url in [self.case_url, self.overview_url]:
            self.assertEqual(403, self.client.get(url).status_code)
        for data in [self.agreement_data(), self.receipt_data()]:
            self.assertEqual(403, self.client.post(self.case_url, data).status_code)
        self.assertFalse(AssociationDepositAccount.objects.exists())

    def test_coop_manage_alone_can_open_and_process_case_without_member_view_permission(
        self,
    ):
        with patch.object(
            TapirUser,
            "has_perm",
            autospec=True,
            side_effect=lambda user, permission, obj=None: permission
            == Permission.Coop.MANAGE,
        ):
            response = self.client.get(self.case_url)
            self.assertEqual(200, response.status_code)
            self.assertEqual(
                302,
                self.client.post(
                    self.case_url, self.agreement_data("0", 1)
                ).status_code,
            )
        self.assertEqual(
            Decimal("0"), AssociationDepositAccount.objects.get().agreed_amount
        )
        self.assertFalse(Payment.objects.exists())

    def test_pending_list_and_case_remain_visible_when_deposit_feature_disabled(self):
        AssociationDepositHardshipRequestRecorder.record_request(
            self.member, self.member, {}
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        response = self.client.get(self.overview_url)
        self.assertContains(response, self.member.email)
        self.assertContains(response, self.case_url)
        response = self.client.get(self.case_url)
        self.assertContains(response, "Individuelle Vereinbarung offen")
        self.assertContains(response, "Zahlungseingang erfassen")
        self.assertNotContains(response, "Dokumentierte Vereinbarung speichern")
        self.assertEqual(
            302, self.client.post(self.case_url, self.receipt_data()).status_code
        )
        account = AssociationDepositAccount.objects.get()
        self.assertEqual(Decimal("25"), account.receipts.get().amount)
        self.assertIsNone(account.agreed_amount)
        self.assertFalse(account.payments.exists())

    def test_other_legal_status_cannot_access_deposit_administration(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_COOPERATIVE
        )
        self.assertEqual(404, self.client.get(self.overview_url).status_code)
        self.assertEqual(
            404,
            self.client.get(self.overview_url, {"member": self.member.pk}).status_code,
        )
        self.assertEqual(
            404, self.client.post(self.case_url, self.receipt_data()).status_code
        )

    def test_admin_can_find_member_without_account_before_recording_external_receipt(
        self,
    ):
        response = self.client.get(self.overview_url, {"member": self.member.pk})
        self.assertRedirects(response, self.case_url)
        self.assertFalse(AssociationDepositAccount.objects.exists())
        data = self.receipt_data()
        self.assertEqual(302, self.client.post(self.case_url, data).status_code)
        self.assertEqual(302, self.client.post(self.case_url, data).status_code)
        account = AssociationDepositAccount.objects.get()
        self.assertIsNone(account.agreed_amount)
        self.assertIsNone(account.effective_from)
        self.assertEqual(1, account.receipts.count())
        self.assertFalse(account.payments.exists())
        response = self.client.post(self.case_url, {**data, "receipt-amount": "26"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.context["receipt_form"].non_field_errors())
        self.assertEqual(1, account.receipts.count())

    def test_pending_case_can_be_reduced_waived_or_scheduled_with_documented_consent(
        self,
    ):
        AssociationDepositHardshipRequestRecorder.record_request(
            self.member, self.member, {}
        )
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("100", 4)).status_code,
        )
        account = AssociationDepositAccount.objects.get()
        self.assertTrue(account.is_individual_agreement)
        self.assertEqual(
            [Decimal("25")] * 4, list(account.payments.values_list("amount", flat=True))
        )
        self.assertEqual(
            [], list(self.client.get(self.overview_url).context["accounts"])
        )
        self.assertContains(
            self.client.get(self.overview_url, {"status": "all"}), self.member.email
        )
        response = self.client.get(self.case_url)
        self.assertContains(response, "Zustimmung dokumentiert")
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("0", 1)).status_code,
        )
        self.assertFalse(account.payments.exists())
        self.assertContains(
            self.client.get(self.case_url), "Vollständiger Verzicht vereinbart"
        )
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("200", 4)).status_code,
        )
        self.assertEqual(
            [Decimal("50")] * 4, list(account.payments.values_list("amount", flat=True))
        )
        self.assertEqual(
            3, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )

    def test_agreement_retry_after_response_loss_does_not_restore_obsolete_terms(self):
        first = self.agreement_data("200", 4)
        self.assertEqual(302, self.client.post(self.case_url, first).status_code)
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("100", 4)).status_code,
        )
        account = AssociationDepositAccount.objects.get()
        original = list(account.payments.order_by("pk").values())
        self.assertEqual(302, self.client.post(self.case_url, first).status_code)
        self.assertEqual(original, list(account.payments.order_by("pk").values()))
        self.assertEqual(
            2, AssociationDepositAgreementAuthorizedLogEntry.objects.count()
        )
        response = self.client.post(self.case_url, {**first, "agreement-amount": "75"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.context["agreement_form"].non_field_errors())
        self.assertEqual(original, list(account.payments.order_by("pk").values()))

    def test_stale_admin_terms_and_missing_consent_have_visible_errors_without_writes(
        self,
    ):
        stale = self.agreement_data()
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("100", 4)).status_code,
        )
        account = AssociationDepositAccount.objects.get()
        original = list(account.payments.order_by("pk").values())
        response = self.client.post(self.case_url, stale)
        self.assertContains(response, "inzwischen geändert")
        response = self.client.post(
            self.case_url, {**self.agreement_data(), "agreement-consent_note": " "}
        )
        self.assertEqual(200, response.status_code)
        self.assertIn("consent_note", response.context["agreement_form"].errors)
        self.assertEqual(original, list(account.payments.order_by("pk").values()))

    def test_receipt_before_agreement_and_later_credit_reduce_only_actual_remaining_rates(
        self,
    ):
        self.assertEqual(
            302, self.client.post(self.case_url, self.receipt_data()).status_code
        )
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("75", 2)).status_code,
        )
        account = AssociationDepositAccount.objects.get()
        self.assertEqual(
            [Decimal("25")] * 2,
            list(
                account.payments.order_by("due_date").values_list("amount", flat=True)
            ),
        )
        self.assertEqual(
            302,
            self.client.post(
                self.case_url, self.receipt_data(reference="bank-2")
            ).status_code,
        )
        self.assertEqual(Decimal("25"), account.payments.get().amount)
        self.assertEqual(
            302,
            self.client.post(self.case_url, self.agreement_data("25", 1)).status_code,
        )
        self.assertFalse(account.payments.exists())
        response = self.client.get(self.case_url)
        self.assertEqual(
            Decimal("25"), response.context["details"]["overpayment_credit"]
        )
        self.assertContains(response, "keine automatische Rückzahlung")

    def test_export_since_receipt_form_requires_reload_but_successful_reference_retry_stays_idempotent(
        self,
    ):
        self.assertEqual(
            302, self.client.post(self.case_url, self.agreement_data()).status_code
        )
        form = self.client.get(self.case_url).context["receipt_form"]
        self.assertEqual(Decimal("0"), form.initial["expected_committed_amount"])
        stale = self.receipt_data()
        PaymentExportBuilder.export_all_unexported_payments(self.today, False, {})
        account = AssociationDepositAccount.objects.get()
        exported = list(account.payments.filter(transaction__isnull=False).values())
        files = list(ExportedFile.objects.order_by("pk").values())
        response = self.client.post(self.case_url, stale)
        self.assertContains(response, "neu laden")
        self.assertFalse(account.receipts.exists())
        self.assertEqual(
            exported, list(account.payments.filter(transaction__isnull=False).values())
        )
        self.assertEqual(files, list(ExportedFile.objects.order_by("pk").values()))
        response = self.client.get(self.case_url)
        self.assertEqual(
            Decimal("50"),
            response.context["receipt_form"].initial["expected_committed_amount"],
        )
        confirmed = self.receipt_data(committed="50")
        self.assertEqual(302, self.client.post(self.case_url, confirmed).status_code)
        self.assertEqual(
            [Decimal("25"), Decimal("50"), Decimal("50")],
            list(
                account.payments.filter(transaction=None)
                .order_by("due_date")
                .values_list("amount", flat=True)
            ),
        )
        PaymentExportBuilder.export_all_unexported_payments(
            datetime.date(2026, 12, 5), False, {}
        )
        before = list(account.payments.order_by("pk").values())
        self.assertEqual(302, self.client.post(self.case_url, confirmed).status_code)
        self.assertEqual(1, account.receipts.count())
        self.assertEqual(before, list(account.payments.order_by("pk").values()))
        response = self.client.post(
            self.case_url, {**confirmed, "receipt-reference": "new-stale-reference"}
        )
        self.assertContains(response, "neu laden")
        self.assertEqual(1, account.receipts.count())
