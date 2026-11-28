import datetime
from decimal import Decimal

from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
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
        member = MemberFactory.create(
            iban=iban,
            last_name=last_name,
            account_owner="Kontoinhaber",
            sepa_consent=consent or datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
        )
        return AssociationMembershipFactory.create(
            member=member, start_date=self.today, end_date=None
        )

    def create_payment(self, membership):
        return AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=membership.member,
            amount=Decimal("200"),
            start_date=membership.start_date,
            actor=membership.member,
            cache={},
        )

    def export(self):
        return PaymentExportBuilder.export_all_unexported_payments(
            reference_date=self.today, send_mail=False, cache={}
        )

    def test_exportAllUnexportedPayments_default_exportsDepositTransaction(
        self,
    ):
        membership = self.create_membership()
        payment = self.create_payment(membership)

        self.export()
        payment.refresh_from_db()
        self.assertEqual(PAYMENT_TYPE_ASSOCIATION_DEPOSIT, payment.transaction.type)

    def test_exportAllUnexportedPayments_memberExcluded_exportsDepositLikeCoopShares(
        self,
    ):
        self._set_parameter(ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, True)
        membership = self.create_membership()
        payment = self.create_payment(membership)
        PaymentExportExclusionPeriodFactory.create(
            member=membership.member, start_date=self.today, end_date=None
        )

        self.assertFalse(
            PaymentExportExclusionPeriodService.is_payment_excluded(
                payment=payment, cache={}
            )
        )
        self.assertFalse(
            Payment.objects.filter(
                PaymentExportExclusionPeriodService.build_payment_is_excluded_condition(
                    cache={}
                ),
                pk=payment.pk,
            ).exists()
        )
        self.assertEqual([], self.export())
        payment.refresh_from_db()
        self.assertIsNotNone(payment.transaction_id)
        self.assertFalse(payment.excluded_from_export)

    def test_exportAllUnexportedPayments_contractNamedLikeDeposit_exportsAsContract(
        self,
    ):
        deposit = self.create_payment(self.create_membership())
        contract = PaymentFactory.create(
            type="Vereinseinlage",
            mandate_ref=deposit.mandate_ref,
            transaction=None,
            due_date=self.today,
            subscription_payment_range_start=self.today.replace(day=1),
            subscription_payment_range_end=self.today.replace(day=30),
        )
        self.assertEqual([], self.export())
        contract.refresh_from_db()
        deposit.refresh_from_db()
        self.assertEqual("Verträge", contract.transaction.type)
        self.assertEqual(PAYMENT_TYPE_ASSOCIATION_DEPOSIT, deposit.transaction.type)
