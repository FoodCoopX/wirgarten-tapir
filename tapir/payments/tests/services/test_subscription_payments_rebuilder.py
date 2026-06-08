import datetime

from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.subscription_payments_rebuilder import (
    SubscriptionPaymentsRebuilder,
)
from tapir.wirgarten.models import Payment, PaymentTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PaymentTransactionFactory,
    PaymentFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSubscriptionPaymentsRebuilder(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2017, month=1, day=1),
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2017, month=7, day=18))

    def test_rebuildSubscriptionPayments_transactionsAreBeforeGivenDate_transactionsNotAffected(
        self,
    ):
        transaction = PaymentTransactionFactory.create(
            month=datetime.date(year=2017, month=6, day=1), type="test_type"
        )
        payment = PaymentFactory.create(transaction=transaction)

        SubscriptionPaymentsRebuilder.rebuild_subscription_payments(
            from_date=datetime.date(year=2017, month=7, day=1), cache={}
        )

        self.assertEqual(1, Payment.objects.count())
        self.assertEqual(payment.id, Payment.objects.get().id)

        self.assertTrue(PaymentTransaction.objects.filter(id=transaction.id).exists())
        self.assertEqual(
            3,
            PaymentTransaction.objects.count(),
            "1 past transaction from the test data, plus 2 on the given month (subscriptions + coop shares)",
        )

    def test_rebuildSubscriptionPayments_transactionForCoopShareExists_transactionNotAffected(
        self,
    ):
        transaction = PaymentTransactionFactory.create(
            month=datetime.date(year=2017, month=7, day=1),
            type=PAYMENT_TYPE_COOP_SHARES,
        )
        payment = PaymentFactory.create(transaction=transaction)

        SubscriptionPaymentsRebuilder.rebuild_subscription_payments(
            from_date=datetime.date(year=2017, month=7, day=1), cache={}
        )

        self.assertEqual(1, Payment.objects.count())
        self.assertEqual(payment.id, Payment.objects.get().id)

        self.assertTrue(PaymentTransaction.objects.filter(id=transaction.id).exists())
        self.assertEqual(
            2,
            PaymentTransaction.objects.count(),
            "1 transaction for coop shares from the test data, 1 new transaction for subscriptions",
        )

    def test_rebuildSubscriptionPayments_transactionsAfterGivenDateExists_transactionsDeletedThenRebuilt(
        self,
    ):
        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2017, month=1, day=1)
        )
        ProductPriceFactory.create(
            product=subscription.product, valid_from=subscription.start_date
        )

        transaction_1 = PaymentTransactionFactory.create(
            month=datetime.date(year=2017, month=6, day=1),
            type=subscription.product.type.name,
        )
        payment_1 = PaymentFactory.create(
            transaction=transaction_1,
            type=subscription.product.type.name,
            mandate_ref__member=subscription.member,
        )

        transaction_2 = PaymentTransactionFactory.create(
            month=datetime.date(year=2017, month=7, day=1),
            type=subscription.product.type.name,
        )
        payment_2 = PaymentFactory.create(
            transaction=transaction_2,
            type=subscription.product.type.name,
            mandate_ref__member=subscription.member,
        )

        SubscriptionPaymentsRebuilder.rebuild_subscription_payments(
            from_date=datetime.date(year=2017, month=7, day=3), cache={}
        )

        self.assertEqual(2, Payment.objects.count())
        self.assertFalse(Payment.objects.filter(id=payment_2.id).exists())
        self.assertTrue(Payment.objects.filter(id=payment_1.id).exists())
