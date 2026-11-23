from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.serializers import PaymentSerializer
from tapir.wirgarten.tests.factories import PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentSerializer(TapirIntegrationTest):
    def test_serialize_associationDeposit_preservesTypeAndAddsLabel(self):
        payment = PaymentFactory.create(type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT)

        data = PaymentSerializer(payment).data

        self.assertEqual(PAYMENT_TYPE_ASSOCIATION_DEPOSIT, data["type"])
        self.assertEqual("Vereinseinlage", data["type_label"])

    def test_serialize_contract_preservesTypeAndLabel(self):
        payment = PaymentFactory.create(type="Gemüse")

        data = PaymentSerializer(payment).data

        self.assertEqual("Gemüse", data["type"])
        self.assertEqual("Gemüse", data["type_label"])
