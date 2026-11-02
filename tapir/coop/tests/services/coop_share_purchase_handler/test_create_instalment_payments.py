import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    CoopShareTransactionFactory,
    MandateReferenceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateInstalmentPayments(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.COOP_SHARES_INSTALMENT_AMOUNT, value=Decimal(20)
        )

    @patch.object(CoopSharePurchaseHandler, "get_payment_due_date", autospec=True)
    def test_createInstalmentPayments_default_createsOnePaymentPerInstalmentEachMonth(
        self, mock_get_payment_due_date: Mock
    ):
        mock_get_payment_due_date.return_value = datetime.date(
            year=2025, month=1, day=31
        )
        transaction = CoopShareTransactionFactory.create(
            quantity=2, share_price=50, mandate_ref=MandateReferenceFactory.create()
        )
        cache = {}

        CoopSharePurchaseHandler.create_instalment_payments(
            coop_share_transaction=transaction, cache=cache
        )

        payments = list(Payment.objects.order_by("instalment_number"))
        self.assertEqual(5, len(payments))
        self.assertEqual([1, 2, 3, 4, 5], [p.instalment_number for p in payments])
        self.assertEqual(
            [
                datetime.date(year=2025, month=1, day=31),
                datetime.date(year=2025, month=2, day=28),
                datetime.date(year=2025, month=3, day=31),
                datetime.date(year=2025, month=4, day=30),
                datetime.date(year=2025, month=5, day=31),
            ],
            [p.due_date for p in payments],
        )
        for payment in payments:
            self.assertEqual(Decimal(20), payment.amount)
            self.assertEqual(transaction, payment.coop_share_transaction)
            self.assertEqual(transaction.mandate_ref, payment.mandate_ref)
            self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
            self.assertEqual(PAYMENT_TYPE_COOP_SHARES, payment.type)
        mock_get_payment_due_date.assert_called_once_with(
            shares_valid_at=transaction.valid_at, cache=cache
        )
