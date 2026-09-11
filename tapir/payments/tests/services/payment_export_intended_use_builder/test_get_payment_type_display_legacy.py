from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetPaymentTypeDisplayLegacy(TapirUnitTest):
    def test_getPaymentTypeDisplayLegacy_contractPayments_returnsCorrectString(self):
        result = PaymentExportIntendedUseBuilder.get_payment_type_display_legacy(
            contract_payments=True
        )

        self.assertEqual("Verträge", result)

    def test_getPaymentTypeDisplayLegacy_coopShares_returnsCoopSharesConstant(self):
        result = PaymentExportIntendedUseBuilder.get_payment_type_display_legacy(
            contract_payments=False
        )

        self.assertEqual(PAYMENT_TYPE_COOP_SHARES, result)
