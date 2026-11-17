from tapir.payments.serializers import PaymentTransactionSerializer
from tapir.wirgarten.tests.factories import PaymentFactory, PaymentTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentTransactionSerializer(TapirIntegrationTest):
    def test_serialize_someExcludedPayments_exportedAndExcludedCountedSeparately(
        self,
    ):
        transaction = PaymentTransactionFactory.create()
        PaymentFactory.create(
            transaction=transaction, amount=10, excluded_from_export=False
        )
        PaymentFactory.create(
            transaction=transaction, amount=20, excluded_from_export=False
        )
        PaymentFactory.create(
            transaction=transaction, amount=50, excluded_from_export=True
        )

        data = PaymentTransactionSerializer(transaction).data

        self.assertEqual(2, data["payments_count"])
        self.assertEqual(30, data["payments_sum"])
        self.assertEqual(1, data["excluded_payments_count"])
        self.assertEqual(50, data["excluded_payments_sum"])
