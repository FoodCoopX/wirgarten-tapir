import datetime
from decimal import Decimal
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.urls import reverse

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.tests.factories import AssociationDepositAccountFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.payments.services.subscription_payments_rebuilder import (
    SubscriptionPaymentsRebuilder,
)
from tapir.products.services.product_type_change_applier import ProductTypeChangeApplier
from tapir.wirgarten.models import Payment, ExportedFile
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentTransactionFactory,
    PaymentFactory,
    ProductTypeFactory,
    ProductCapacityFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositPaymentIntegration(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.PAYMENT_DUE_DAY, 5)
        self._set_parameter(ParameterKeys.PAYMENT_START_DATE, "2026-11-01")
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.today = datetime.date(2026, 11, 5)
        self.member = MemberFactory()
        AssociationMembershipFactory(
            member=self.member, start_date=self.today, end_date=None
        )
        self.account = AssociationDepositAccountFactory(
            member=self.member, agreed_amount=Decimal("200"), effective_from=self.today
        )
        self.payment = (
            AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
                self.member, self.member, {}
            )
        )

    def test_legacy_contract_selection_excludes_deposit_payments(self):
        self.assertFalse(
            PaymentExportBuilder.get_unexported_payments(self.today).exists()
        )

    def test_future_payments_response_supports_deposit_without_contract_dates(self):
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_NAME, "Investitionsbeitrag"
        )
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("payments:member_future_payments"), {"member_id": self.member.pk}
        )
        self.assertEqual(200, response.status_code, response.content)
        rows = [
            row
            for row in response.json()["payments"]
            if row["payment"]["id"] == self.payment.pk
        ]
        self.assertEqual(1, len(rows))
        self.assertEqual(
            self.account.pk, rows[0]["payment"]["association_deposit_account"]
        )
        self.assertEqual("Investitionsbeitrag", rows[0]["association_deposit_name"])
        self.assertEqual([], rows[0]["subscriptions"])
        self.assertEqual([], rows[0]["association_memberships"])

    def test_export_details_support_existing_deposit_history(self):
        transaction = PaymentTransactionFactory(
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT, month=self.today
        )
        self.payment.transaction = transaction
        self.payment.status = Payment.PaymentStatus.PAID
        self.payment.save()
        self.client.force_login(MemberFactory(is_superuser=True))

        response = self.client.get(
            reverse("payments:payment_transaction_details"),
            {"transaction_id": transaction.pk},
        )
        self.assertEqual(200, response.status_code, response.content)
        self.assertIn(
            "Vereinseinlage",
            response.json()["intended_use_by_mandate_ref"][self.payment.mandate_ref_id],
        )

    def assert_rebuild_preserves_payments(self, rebuild):
        transaction = PaymentTransactionFactory(
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT, month=self.today
        )
        self.payment.transaction = transaction
        self.payment.status = Payment.PaymentStatus.PAID
        self.payment.save()
        another = MemberFactory()
        AssociationMembershipFactory(
            member=another, start_date=self.today, end_date=None
        )
        AssociationDepositAccountFactory(
            member=another, agreed_amount=200, effective_from=self.today
        )
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            another, another, {}
        )
        before = list(
            Payment.objects.filter(association_deposit_account__isnull=False)
            .order_by("pk")
            .values()
        )
        csv_bytes = bytes(transaction.csv_file.file)
        rebuild()
        self.assertEqual(
            before,
            list(
                Payment.objects.filter(association_deposit_account__isnull=False)
                .order_by("pk")
                .values()
            ),
        )
        transaction.csv_file.refresh_from_db()
        self.assertEqual(csv_bytes, bytes(transaction.csv_file.file))

    def test_subscription_rebuild_preserves_open_and_exported_deposit_payments(self):
        self.assert_rebuild_preserves_payments(
            lambda: SubscriptionPaymentsRebuilder.rebuild_subscription_payments(
                self.today.replace(day=1), {}
            )
        )

    def test_history_rebuild_preserves_open_and_exported_deposit_payments(self):
        self.assert_rebuild_preserves_payments(
            lambda: call_command("rebuild_payment_history", no_confirm=True)
        )

    def test_subscription_import_preserves_open_and_exported_deposit_payments(self):
        with NamedTemporaryFile(mode="w", suffix=".csv") as csv_file:
            csv_file.write("Mitgliedernummer\n")
            csv_file.flush()
            self.assert_rebuild_preserves_payments(
                lambda: call_command(
                    "import-data",
                    "--type",
                    "subscriptions",
                    "--file",
                    csv_file.name,
                    "--delete-all",
                )
            )

    def test_product_rename_does_not_change_deposit_history_with_same_type_name(self):
        transaction = PaymentTransactionFactory(
            type=self.payment.type, month=self.today
        )
        self.payment.status = Payment.PaymentStatus.PAID
        self.payment.transaction = transaction
        self.payment.save()
        original = list(self.account.payments.values())
        contract_payment = PaymentFactory(
            type=self.payment.type,
            mandate_ref=self.payment.mandate_ref,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
        )
        product_type = ProductTypeFactory(name=self.payment.type)
        capacity = ProductCapacityFactory(product_type=product_type)
        data = {
            field: getattr(product_type, field)
            for field in ProductTypeChangeApplier.direct_fields
        }
        data.update(
            name="Neue Produktgruppe",
            capacity=capacity.capacity,
            tax_rate=7,
            tax_rate_change_date=self.today,
            accordions_in_bestell_wizard=[],
            custom_cycle_delivery_weeks={},
        )

        ProductTypeChangeApplier.apply_changes(product_type, data, capacity)

        self.assertEqual(original, list(self.account.payments.values()))
        contract_payment.refresh_from_db()
        self.assertEqual("Neue Produktgruppe", contract_payment.type)

    def test_contract_with_deposit_type_name_is_not_offset_by_deposit_payment(self):
        period = GrowingPeriodFactory(
            start_date=datetime.date(2026, 11, 1), end_date=datetime.date(2027, 10, 31)
        )
        subscription = SubscriptionFactory(
            member=self.member, quantity=1, period=period
        )
        subscription.product.type.name = PAYMENT_TYPE_ASSOCIATION_DEPOSIT
        subscription.product.type.save()
        ProductPriceFactory(
            product=subscription.product,
            price=10,
            valid_from=subscription.period.start_date,
        )
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("payments:member_future_payments"), {"member_id": self.member.pk}
        )
        self.assertEqual(200, response.status_code, response.content)
        contracts = [
            row
            for row in response.json()["payments"]
            if row["payment"]["type"] == PAYMENT_TYPE_ASSOCIATION_DEPOSIT
            and row["payment"]["association_deposit_account"] is None
        ]
        self.assertTrue(contracts)
        self.assertTrue(any(row["payment"]["amount"] > 0 for row in contracts))
        self.assertTrue(all(row["subscriptions"] for row in contracts))
