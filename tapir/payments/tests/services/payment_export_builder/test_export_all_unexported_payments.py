import datetime

from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.models import Payment, Member, PaymentTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PaymentFactory,
    MandateReferenceFactory,
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExportAllUnexportedPayments(TapirIntegrationTest):
    REFERENCE_DATE = datetime.date(year=2026, month=6, day=1)

    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN, value="NL88ABNA2011060885"
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, value="test_id"
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, value=False
        )
        cls._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
            value=LEGAL_STATUS_COOPERATIVE,
        )

    def setUp(self) -> None:
        super().setUp()
        self.excluded_member = MemberFactory.create(iban="DE89370400440532013000")
        self.other_member = MemberFactory.create(iban="NL91ABNA0417164300")

    def test_exportAllUnexportedPayments_memberExcludedAtDueDate_paymentNotInFilesButMarkedAsPaid(
        self,
    ):
        PaymentExportExclusionPeriodFactory.create(
            member=self.excluded_member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        excluded_payment = self._create_payment(member=self.excluded_member)
        other_payment = self._create_payment(member=self.other_member)

        self._export()

        self._assert_member_not_in_files(member=self.excluded_member)
        self._assert_member_in_files(member=self.other_member)
        excluded_payment.refresh_from_db()
        self.assertEqual(Payment.PaymentStatus.PAID, excluded_payment.status)
        self.assertIsNotNone(excluded_payment.transaction)
        self.assertTrue(excluded_payment.excluded_from_export)
        other_payment.refresh_from_db()
        self.assertFalse(other_payment.excluded_from_export)

    def test_exportAllUnexportedPayments_featureDisabled_paymentIsExported(self):
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )
        PaymentExportExclusionPeriodFactory.create(
            member=self.excluded_member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=None,
        )
        self._create_payment(member=self.excluded_member)

        self._export()

        self._assert_member_in_files(member=self.excluded_member)

    def test_exportAllUnexportedPayments_dueDateBeforePeriod_paymentIsExported(
        self,
    ):
        PaymentExportExclusionPeriodFactory.create(
            member=self.excluded_member,
            start_date=datetime.date(year=2026, month=6, day=2),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        self._create_payment(member=self.excluded_member)

        self._export()

        self._assert_member_in_files(member=self.excluded_member)

    def test_exportAllUnexportedPayments_dueDateAfterPeriod_paymentIsExported(
        self,
    ):
        PaymentExportExclusionPeriodFactory.create(
            member=self.excluded_member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=5, day=31),
        )
        self._create_payment(member=self.excluded_member)

        self._export()

        self._assert_member_in_files(member=self.excluded_member)

    def test_exportAllUnexportedPayments_periodWithoutEndDate_paymentNotInFiles(
        self,
    ):
        PaymentExportExclusionPeriodFactory.create(
            member=self.excluded_member,
            start_date=datetime.date(year=2020, month=1, day=1),
            end_date=None,
        )
        self._create_payment(member=self.excluded_member)
        self._create_payment(member=self.other_member)

        self._export()

        self._assert_member_not_in_files(member=self.excluded_member)
        self._assert_member_in_files(member=self.other_member)

    def test_exportAllUnexportedPayments_coopSharePaymentOfExcludedMember_paymentIsExported(
        self,
    ):
        PaymentExportExclusionPeriodFactory.create(
            member=self.excluded_member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=None,
        )
        self._create_payment(
            member=self.excluded_member, payment_type=PAYMENT_TYPE_COOP_SHARES
        )

        self._export()

        self._assert_member_in_files(member=self.excluded_member)

    def _create_payment(self, member: Member, payment_type: str = "Gemüse") -> Payment:
        return PaymentFactory.create(
            mandate_ref=MandateReferenceFactory.create(member=member),
            due_date=self.REFERENCE_DATE,
            type=payment_type,
            status=Payment.PaymentStatus.DUE,
            transaction=None,
            subscription_payment_range_start=self.REFERENCE_DATE,
            subscription_payment_range_end=datetime.date(year=2026, month=6, day=30),
        )

    def _export(self) -> None:
        PaymentExportBuilder.export_all_unexported_payments(
            reference_date=self.REFERENCE_DATE, send_mail=False, cache={}
        )

    def _get_files_content(self) -> str:
        contents = []
        for transaction in PaymentTransaction.objects.all():
            contents.append(bytes(transaction.csv_file.file).decode())
            if transaction.xml_file is not None:
                contents.append(bytes(transaction.xml_file.file).decode())
        return "\n".join(contents)

    def _assert_member_in_files(self, member: Member) -> None:
        self.assertIn(member.iban, self._get_files_content())

    def _assert_member_not_in_files(self, member: Member) -> None:
        self.assertNotIn(member.iban, self._get_files_content())
