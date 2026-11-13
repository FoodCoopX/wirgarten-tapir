import datetime
from decimal import Decimal
from unittest.mock import patch
from xml.etree import ElementTree

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDepositAgreedLogEntry
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypeFactory,
)
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.payments.services.subscription_payments_rebuilder import (
    SubscriptionPaymentsRebuilder,
)
from tapir.payments.tasks import export_payments_for_this_month
from tapir.wirgarten.models import Payment, PaymentTransaction, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PaymentFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPaymentExportBuilderAssociationDeposits(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.today = datetime.date(2026, 11, 5)
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        for key, value in (
            (ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True),
            (ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION),
            (ParameterKeys.PAYMENT_DUE_DAY, 5),
            (ParameterKeys.PAYMENT_ORGANISATION_IBAN, "NL88ABNA2011060885"),
            (ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, "DE98ZZZ09999999999"),
        ):
            self._set_parameter(key, value)

    def create_membership(
        self, iban="NL88ABNA2011060885", last_name="Testperson", consent=None
    ):
        member = MemberFactory(
            iban=iban,
            last_name=last_name,
            account_owner="Kontoinhaber",
            sepa_consent=consent or datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
        )
        return AssociationMembershipFactory(
            member=member, start_date=self.today, end_date=None
        )

    def create_payment(self, membership):
        return AssociationDepositPaymentCreator.create_payment(
            membership, Decimal("200"), membership.member, {}
        )

    def export(self):
        return PaymentExportBuilder.export_all_unexported_payments(
            self.today, False, {}
        )

    def test_exportAllUnexportedPayments_retried_exportedDebitAndAuditRemainUnique(
        self,
    ):
        membership = self.create_membership()
        payment = self.create_payment(membership)
        self.assertEqual(payment.pk, self.create_payment(membership).pk)
        self.assertEqual(1, AssociationDepositAgreedLogEntry.objects.count())

        self.assertEqual([], self.export())
        payment.refresh_from_db()
        self.assertEqual(Payment.PaymentStatus.PAID, payment.status)
        self.assertEqual(PAYMENT_TYPE_ASSOCIATION_DEPOSIT, payment.transaction.type)
        xml = ElementTree.fromstring(bytes(payment.transaction.xml_file.file))
        self.assertEqual(
            ["200.00"], [node.text for node in xml.findall(".//{*}InstdAmt")]
        )
        self.assertEqual(payment.mandate_ref_id, xml.findtext(".//{*}MndtId"))
        self.assertEqual(self.today.isoformat(), xml.findtext(".//{*}ReqdColltnDt"))
        self.assertEqual([], self.export())
        self.assertEqual(
            1,
            PaymentTransaction.objects.filter(
                type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            ).count(),
        )

    def test_exportAllUnexportedPayments_reusedMandate_usesSameSignatureDateInCsvAndXml(
        self,
    ):
        payment = self.create_payment(self.create_membership())
        mandate = payment.mandate_ref
        mandate.start_ts = datetime.datetime(2026, 10, 29, tzinfo=datetime.UTC)
        mandate.save(update_fields=["start_ts"])

        self.assertEqual([], self.export())
        payment.refresh_from_db()
        xml = ElementTree.fromstring(bytes(payment.transaction.xml_file.file))
        self.assertEqual("2026-10-29", xml.findtext(".//{*}DtOfSgntr"))
        csv = bytes(payment.transaction.csv_file.file).decode()
        self.assertIn("29.10.2026", csv)
        self.assertNotIn("01.11.2026", csv)

    def test_exportAllUnexportedPayments_invalidMember_exportsOnlyValidPayment(self):
        valid = self.create_payment(self.create_membership(last_name="Gueltig"))
        invalid = self.create_payment(
            self.create_membership(iban="INVALID", last_name="Ungueltig")
        )

        self.assertEqual(1, len(self.export()))
        invalid.refresh_from_db()
        valid.refresh_from_db()
        self.assertEqual(Payment.PaymentStatus.DUE, invalid.status)
        self.assertIsNone(invalid.transaction_id)
        csv = bytes(valid.transaction.csv_file.file).decode()
        self.assertIn("Gueltig", csv)
        self.assertNotIn("Ungueltig", csv)
        xml = ElementTree.fromstring(bytes(valid.transaction.xml_file.file))
        self.assertEqual(valid.mandate_ref_id, xml.findtext(".//{*}MndtId"))
        self.assertEqual(1, len(xml.findall(".//{*}DrctDbtTxInf")))

    def test_exportAllUnexportedPayments_membershipEnded_doesNotExportDeposit(self):
        membership = self.create_membership()
        payment = self.create_payment(membership)
        membership.end_date = self.today - datetime.timedelta(days=1)
        membership.save(update_fields=["end_date"])
        AssociationMembershipChangeHandler.start_membership(
            membership.member,
            AssociationMembershipTypeFactory(),
            self.today + datetime.timedelta(days=1),
            membership.member,
            {},
        )
        self.assertEqual([], self.export())
        payment.refresh_from_db()
        self.assertIsNone(payment.transaction_id)
        self.assertEqual(
            1, Payment.objects.filter(type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT).count()
        )

    def test_exportAllUnexportedPayments_continuousMembershipChange_keepsAgreedDebit(
        self,
    ):
        membership = self.create_membership()
        payment = self.create_payment(membership)
        replacement = AssociationMembershipChangeHandler.start_membership(
            membership.member,
            AssociationMembershipTypeFactory(),
            self.today,
            membership.member,
            {},
        )
        self.assertEqual(payment.pk, self.create_payment(replacement).pk)
        self.assertEqual([], self.export())
        payment.refresh_from_db()
        self.assertIsNotNone(payment.transaction_id)

    def test_exportAllUnexportedPayments_futureMembershipChange_keepsOriginalCollectionDate(
        self,
    ):
        membership = self.create_membership()
        payment = self.create_payment(membership)
        AssociationMembershipChangeHandler.start_membership(
            membership.member,
            AssociationMembershipTypeFactory(),
            self.today + datetime.timedelta(days=7),
            membership.member,
            {},
        )

        self.assertEqual([], self.export())
        payment.refresh_from_db()
        xml = ElementTree.fromstring(bytes(payment.transaction.xml_file.file))
        self.assertEqual(self.today.isoformat(), xml.findtext(".//{*}ReqdColltnDt"))

    def test_createPayment_rescheduledMembershipChange_reusesAgreedDebit(self):
        membership = self.create_membership()
        payment = self.create_payment(membership)
        next_type = AssociationMembershipTypeFactory()
        AssociationMembershipChangeHandler.start_membership(
            membership.member,
            next_type,
            self.today + datetime.timedelta(days=20),
            membership.member,
            {},
        )
        rescheduled = AssociationMembershipChangeHandler.start_membership(
            membership.member,
            next_type,
            self.today + datetime.timedelta(days=10),
            membership.member,
            {},
        )
        self.assertEqual(payment.pk, self.create_payment(rescheduled).pk)
        self.assertEqual([], self.export())
        payment.refresh_from_db()
        self.assertIsNotNone(payment.transaction_id)

    def test_exportAllUnexportedPayments_shortMonth_usesTheActualCollectionDate(self):
        mock_timezone(self, datetime.datetime(2026, 2, 10, 12))
        self.today = datetime.date(2026, 2, 10)
        self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, 31)
        membership = self.create_membership(
            consent=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC)
        )
        payment = self.create_payment(membership)
        self.assertEqual([], self.export())
        payment.refresh_from_db()
        xml = ElementTree.fromstring(bytes(payment.transaction.xml_file.file))
        self.assertEqual("2026-02-28", xml.findtext(".//{*}ReqdColltnDt"))

    def test_getUnexportedPayments_productWithDepositName_isStillAContractPayment(self):
        ordinary = PaymentFactory(
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT, transaction=None, due_date=self.today
        )
        deposit = self.create_payment(self.create_membership())
        payments = PaymentExportBuilder.get_unexported_payments(self.today)
        self.assertIn(ordinary, payments)
        self.assertNotIn(deposit, payments)

    def test_createPayment_cooperative_rejectsDeposit(self):
        membership = self.create_membership()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_COOPERATIVE
        )
        with self.assertRaises(ValidationError):
            self.create_payment(membership)
        self.assertFalse(
            Payment.objects.filter(type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT).exists()
        )

    def create_subscription_for_deposit_member(self, deposit):
        month_start = self.today.replace(day=1)
        self._set_parameter(ParameterKeys.PAYMENT_START_DATE, month_start)
        self._set_parameter(ParameterKeys.TRIAL_PERIOD_ENABLED, False)
        subscription = SubscriptionFactory(
            member=deposit.mandate_ref.member,
            mandate_ref=deposit.mandate_ref,
            period=GrowingPeriodFactory(start_date=month_start),
            product__type__name=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            quantity=1,
        )
        Subscription.objects.filter(pk=subscription.pk).update(
            created_at=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC)
        )
        ProductPriceFactory(
            product=subscription.product, price=10, valid_from=month_start
        )

    def test_exportAllUnexportedPayments_productWithDepositName_exportsBothDebits(self):
        membership = self.create_membership()
        deposit = self.create_payment(membership)
        self.create_subscription_for_deposit_member(deposit)
        self.assertEqual(
            [], export_payments_for_this_month(self.today, send_mail=False)
        )
        deposit.refresh_from_db()
        contract = Payment.objects.get(
            mandate_ref=deposit.mandate_ref,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            association_deposit__isnull=True,
        )
        self.assertEqual(Decimal("10"), contract.amount)
        self.assertEqual(Decimal("200"), deposit.amount)
        self.assertNotEqual(contract.transaction_id, deposit.transaction_id)
        self.assertIsNotNone(contract.transaction_id)
        self.assertIsNotNone(deposit.transaction_id)

    def test_exportAllUnexportedPayments_depositExportFails_preservesContractExport(
        self,
    ):
        deposit = self.create_payment(self.create_membership())
        self.create_subscription_for_deposit_member(deposit)

        with patch.object(
            PaymentExportBuilder,
            "_export_association_deposits",
            side_effect=RuntimeError("Deposit export failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Deposit export failed"):
                export_payments_for_this_month(self.today, send_mail=False)

        contract = Payment.objects.get(
            mandate_ref=deposit.mandate_ref, association_deposit__isnull=True
        )
        self.assertIsNotNone(contract.transaction_id)
        self.assertEqual(
            [], export_payments_for_this_month(self.today, send_mail=False)
        )
        self.assertEqual(1, PaymentTransaction.objects.filter(type="Verträge").count())

    def test_exportAllUnexportedPayments_rebuild_preservesExportedAndPendingDeposits(
        self,
    ):
        exported = self.create_payment(self.create_membership())
        self.export()
        exported.refresh_from_db()
        pending = self.create_payment(self.create_membership())

        self.assertEqual(
            [],
            SubscriptionPaymentsRebuilder.rebuild_subscription_payments(self.today, {}),
        )
        transaction_id = exported.transaction_id
        exported.refresh_from_db()
        pending.refresh_from_db()
        self.assertIsNotNone(transaction_id)
        self.assertEqual(transaction_id, exported.transaction_id)
        self.assertIsNone(pending.transaction_id)
