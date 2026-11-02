import datetime
from unittest.mock import patch, Mock

from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    CoopShareTransactionFactory,
    MandateReferenceFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreatePayment(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(CoopSharePurchaseHandler, "get_payment_due_date", autospec=True)
    def test_createPayment_default_createsPaymentLinkedToTransaction(
        self, mock_get_payment_due_date: Mock
    ):
        due_date = datetime.date(year=2025, month=6, day=8)
        mock_get_payment_due_date.return_value = due_date
        transaction = CoopShareTransactionFactory.create(
            quantity=3,
            share_price=50,
            mandate_ref=MandateReferenceFactory.create(),
        )
        cache = {}

        result = CoopSharePurchaseHandler.create_payment(
            coop_share_transaction=transaction, cache=cache
        )

        result.refresh_from_db()
        self.assertEqual(150, result.amount)
        self.assertEqual(due_date, result.due_date)
        self.assertEqual(transaction, result.coop_share_transaction)
        self.assertEqual(transaction.mandate_ref, result.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, result.status)
        self.assertEqual(PAYMENT_TYPE_COOP_SHARES, result.type)
        self.assertIsNone(result.instalment_number)
        mock_get_payment_due_date.assert_called_once_with(
            shares_valid_at=transaction.valid_at, cache=cache
        )

    @patch.object(CoopSharePurchaseHandler, "get_payment_due_date", autospec=True)
    def test_createPayment_paymentAlreadyExistsAtDueDate_createsSeparatePayment(
        self, mock_get_payment_due_date: Mock
    ):
        due_date = datetime.date(year=2025, month=6, day=8)
        mock_get_payment_due_date.return_value = due_date
        first_transaction = CoopShareTransactionFactory.create(
            quantity=2, share_price=50, mandate_ref=MandateReferenceFactory.create()
        )
        first_payment = PaymentFactory.create(
            coop_share_transaction=first_transaction,
            mandate_ref=first_transaction.mandate_ref,
            due_date=due_date,
            amount=100,
            status=Payment.PaymentStatus.DUE,
            transaction=None,
        )
        second_transaction = CoopShareTransactionFactory.create(
            member=first_transaction.member,
            mandate_ref=first_transaction.mandate_ref,
            quantity=3,
            share_price=50,
        )

        result = CoopSharePurchaseHandler.create_payment(
            coop_share_transaction=second_transaction, cache={}
        )

        self.assertNotEqual(first_payment.id, result.id)
        first_payment.refresh_from_db()
        self.assertEqual(100, first_payment.amount)
        self.assertEqual(150, result.amount)
        self.assertEqual(second_transaction, result.coop_share_transaction)
