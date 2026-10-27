from decimal import Decimal

from tapir.coop.services.token_builder_coop_entry import TokenBuilderCoopEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    CoopShareTransactionFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildPaymentMethod(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_buildPaymentMethod_singlePayment_returnsOneTime(self):
        transaction = CoopShareTransactionFactory.create()
        PaymentFactory.create(coop_share_transaction=transaction)

        result = TokenBuilderCoopEntry.build_payment_method(transaction)

        self.assertEqual("einmalig", result)

    def test_buildPaymentMethod_instalments_returnsNumberAndAmountOfInstalments(
        self,
    ):
        transaction = CoopShareTransactionFactory.create()
        for number in [1, 2, 3]:
            PaymentFactory.create(
                coop_share_transaction=transaction,
                instalment_number=number,
                amount=Decimal("12.5"),
            )

        result = TokenBuilderCoopEntry.build_payment_method(transaction)

        self.assertEqual("in 3 monatlichen Raten à 12,50 €", result)
