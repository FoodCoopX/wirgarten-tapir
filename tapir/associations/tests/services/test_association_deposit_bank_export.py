import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from lxml import etree

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.tests.factories import AssociationDepositAccountFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.pain_008_xml_file_creator import Pain008XmlFileCreator
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import Member, Payment, PaymentTransaction, ExportedFile
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositBankExport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        for key, value in [
            (ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True),
            (ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION),
            (ParameterKeys.PAYMENT_DUE_DAY, 5),
            (ParameterKeys.PAYMENT_ORGANISATION_IBAN, "NL88ABNA2011060885"),
            (ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, "DE98ZZZ09999999999"),
            (ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, False),
            (ParameterKeys.PAYMENT_SEND_CSV_FILE_PER_MAIL, True),
            (ParameterKeys.PAYMENT_SEND_XML_FILE_PER_MAIL, True),
        ]:
            self._set_parameter(key, value)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.today = datetime.date(2026, 11, 5)
        self.member, self.account, self.payment = self.prepare_member()

    def prepare_member(self, iban="NL88ABNA2011060885", amount="200"):
        member = MemberFactory(
            iban=iban,
            account_owner="Kontoinhaber",
            sepa_consent=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
        )
        AssociationMembershipFactory(
            member=member, start_date=self.today, end_date=None
        )
        account = AssociationDepositAccountFactory(
            member=member, agreed_amount=Decimal(amount), effective_from=self.today
        )
        payment = AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            member, member, {}
        )
        return member, account, payment

    def export(self, send_mail=False, reference_date=None):
        return PaymentExportBuilder.export_association_deposit_payments(
            reference_date or self.today, send_mail, {}
        )

    def xml_values(self, file, element):
        root = etree.fromstring(bytes(file.file))
        return root.xpath(
            f"//p:{element}/text()",
            namespaces={"p": "urn:iso:std:iso:20022:tech:xsd:pain.008.001.08"},
        )

    def test_existing_pipeline_exports_one_deposit_and_retry_keeps_files_and_payment(
        self,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(
                [],
                PaymentExportBuilder.export_all_unexported_payments(
                    self.today, True, {}
                ),
            )
            self.assertFalse(mail.outbox)
        self.payment.refresh_from_db()
        self.assertEqual(Payment.PaymentStatus.PAID, self.payment.status)
        self.assertEqual(
            PAYMENT_TYPE_ASSOCIATION_DEPOSIT, self.payment.transaction.type
        )
        xml = self.payment.transaction.xml_file
        self.assertEqual(["200.00"], self.xml_values(xml, "InstdAmt"))
        self.assertEqual(["2026-11-05"], self.xml_values(xml, "ReqdColltnDt"))
        self.assertIn("Vereinseinlage", self.xml_values(xml, "Ustrd")[0])
        before_payments = list(self.account.payments.values())
        before_files = list(ExportedFile.objects.order_by("pk").values())
        sent = len(mail.outbox)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(
                [],
                PaymentExportBuilder.export_all_unexported_payments(
                    self.today, True, {}
                ),
            )
        self.assertEqual(before_payments, list(self.account.payments.values()))
        self.assertEqual(
            before_files, list(ExportedFile.objects.order_by("pk").values())
        )
        self.assertEqual(sent, len(mail.outbox))

    def test_cent_amounts_and_external_receipts_are_reflected_in_both_files(self):
        self.account.agreed_amount = Decimal("200.03")
        self.account.save()
        AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("25.01"),
            self.today,
            "cent-receipt",
            "Kontoauszug",
            self.member,
            {},
        )
        self.assertEqual([], self.export())
        self.payment.refresh_from_db()
        self.assertEqual(Decimal("175.02"), self.payment.amount)
        self.assertEqual(
            ["175.02"], self.xml_values(self.payment.transaction.xml_file, "InstdAmt")
        )
        self.assertIn("175,02", bytes(self.payment.transaction.csv_file.file).decode())

    def test_only_valid_payments_are_exported_and_fixed_member_can_retry_same_month(
        self,
    ):
        invalid_member, invalid_account, invalid = self.prepare_member(iban="INVALID")
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(1, len(self.export(send_mail=True)))
        self.payment.refresh_from_db()
        invalid.refresh_from_db()
        self.assertIsNotNone(self.payment.transaction_id)
        self.assertIsNone(invalid.transaction_id)
        self.assertEqual(Payment.PaymentStatus.DUE, invalid.status)
        self.assertEqual(2, len(mail.outbox))
        first_files = list(ExportedFile.objects.order_by("pk").values())
        Member.objects.filter(pk=invalid_member.pk).update(iban="NL88ABNA2011060885")
        self.assertEqual([], self.export())
        invalid.refresh_from_db()
        self.assertIsNotNone(invalid.transaction_id)
        self.assertNotEqual(self.payment.transaction_id, invalid.transaction_id)
        self.assertEqual(
            first_files,
            list(
                ExportedFile.objects.filter(pk__in=[row["id"] for row in first_files])
                .order_by("pk")
                .values()
            ),
        )
        self.assertEqual(
            2,
            PaymentTransaction.objects.filter(
                type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            ).count(),
        )

    def assert_failed_export_keeps_payment_and_notifies(self):
        before = list(self.account.payments.values())
        with self.captureOnCommitCallbacks(execute=True):
            errors = PaymentExportBuilder.export_all_unexported_payments(
                self.today, True, {}
            )
            self.assertFalse(mail.outbox)
        self.assertTrue(errors)
        self.assertEqual(before, list(self.account.payments.values()))
        self.assertFalse(
            ExportedFile.objects.filter(name__startswith="Vereinseinlage-").exists()
        )
        self.assertFalse(
            PaymentTransaction.objects.filter(
                type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            ).exists()
        )
        error_mails = [
            message for message in mail.outbox if message.subject.startswith("Fehler")
        ]
        self.assertEqual(1, len(error_mails))
        self.assertFalse(error_mails[0].attachments)

    def test_all_invalid_payments_notify_without_export_or_paid_status(self):
        Member.objects.filter(pk=self.member.pk).update(iban="INVALID")
        self.assert_failed_export_keeps_payment_and_notifies()

    def test_global_xml_failure_notifies_without_export_or_paid_status(self):
        self._set_parameter(ParameterKeys.PAYMENT_ORGANISATION_IBAN, "INVALID")
        self.assert_failed_export_keeps_payment_and_notifies()

    def test_validation_failure_without_mail_returns_errors_and_leaves_payment_open(
        self,
    ):
        Member.objects.filter(pk=self.member.pk).update(sepa_consent=None)
        self.assertTrue(self.export())
        self.payment.refresh_from_db()
        self.assertIsNone(self.payment.transaction_id)
        self.assertFalse(ExportedFile.objects.exists())
        self.assertFalse(mail.outbox)

    def test_agreed_due_date_is_not_replaced_by_earlier_monthly_collection(self):
        due = self.today.replace(day=20)
        Payment.objects.filter(pk=self.payment.pk).update(due_date=due)
        mock_timezone(self, datetime.datetime(2026, 11, 1, 12))
        self.assertEqual([], self.export(reference_date=datetime.date(2026, 11, 1)))
        self.payment.refresh_from_db()
        self.assertEqual(due, self.payment.due_date)
        self.assertIsNone(self.payment.transaction_id)
        self.assertFalse(ExportedFile.objects.exists())
        mock_timezone(self, datetime.datetime(2026, 11, 20, 12))
        self.assertEqual([], self.export(reference_date=due))
        self.payment.refresh_from_db()
        self.assertEqual(datetime.date(2026, 12, 5), self.payment.due_date)
        self.assertEqual(
            ["2026-12-05"],
            self.xml_values(self.payment.transaction.xml_file, "ReqdColltnDt"),
        )

    def test_new_mandate_start_after_planned_due_date_prevents_collection(self):
        mandate = self.payment.mandate_ref
        mandate.start_ts = datetime.datetime(2026, 12, 1, tzinfo=datetime.UTC)
        mandate.save()
        self.assertTrue(self.export())
        self.payment.refresh_from_db()
        self.assertIsNone(self.payment.transaction_id)
        self.assertFalse(ExportedFile.objects.exists())

    def test_deposit_file_failure_rolls_back_contract_exports_without_sending_files(
        self,
    ):
        contract = PaymentFactory(
            mandate_ref=self.payment.mandate_ref,
            amount=25,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            due_date=self.today,
            type="Ernteanteil",
            subscription_payment_range_start=self.today.replace(day=1),
            subscription_payment_range_end=self.today,
        )
        create_xml = Pain008XmlFileCreator.create_xml_file_from_bytes
        reached_files = []

        def fail_second_xml(xml_bytes, file_name, send_mail, cache, errors):
            reached_files.append(file_name)
            if len(reached_files) == 2:
                self.assertEqual(1, PaymentTransaction.objects.count())
                self.assertEqual(3, ExportedFile.objects.count())
                self.assertIsNotNone(Payment.objects.get(pk=contract.pk).transaction_id)
                self.assertFalse(mail.outbox)
                raise RuntimeError("Einlagendatei konnte nicht gespeichert werden")
            return create_xml(xml_bytes, file_name, send_mail, cache, errors)

        with self.captureOnCommitCallbacks(execute=True), patch.object(
            Pain008XmlFileCreator,
            "create_xml_file_from_bytes",
            side_effect=fail_second_xml,
        ) as save_xml:
            with self.assertRaises(RuntimeError):
                PaymentExportBuilder.export_all_unexported_payments(
                    self.today, True, {}
                )
        self.assertEqual(2, save_xml.call_count)
        self.assertTrue(reached_files[0].startswith("Verträge-"))
        self.assertTrue(reached_files[1].startswith("Vereinseinlage-"))
        self.assertFalse(mail.outbox)
        self.assertFalse(ExportedFile.objects.exists())
        self.assertFalse(PaymentTransaction.objects.exists())
        contract.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertIsNone(contract.transaction_id)
        self.assertIsNone(self.payment.transaction_id)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(
                [],
                PaymentExportBuilder.export_all_unexported_payments(
                    self.today, True, {}
                ),
            )
        self.assertEqual(4, len(mail.outbox))
        self.assertEqual(2, PaymentTransaction.objects.count())
