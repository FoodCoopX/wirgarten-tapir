import datetime
from unittest.mock import patch, Mock

from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateOrUpdatePayment(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(CoopSharePurchaseHandler, "get_payment_due_date")
    def test_createOrUpdatePayment_paymentAlreadyExistsAtDueDate_existingPaymentUpdated(
        self, mock_get_payment_due_date: Mock
    ):
        shares_valid_at = datetime.date(year=2025, month=6, day=3)
        due_date = datetime.date(year=2025, month=6, day=8)
        mock_get_payment_due_date.return_value = due_date
        payment = PaymentFactory.create(
            due_date=due_date,
            amount=120,
            status=Payment.PaymentStatus.DUE,
            type="Genossenschaftsanteile",
        )
        cache = {}

        result = CoopSharePurchaseHandler.create_or_update_payment(
            shares_valid_at=shares_valid_at,
            mandate_ref=payment.mandate_ref,
            quantity=3,
            cache=cache,
        )

        self.assertEqual(payment.id, result.id)
        self.assertEqual(
            270, result.amount
        )  # 120 from before plus 3*50 for the 3 new shares
        self.assertEqual(1, Payment.objects.count())  # no payment created

    @patch.object(CoopSharePurchaseHandler, "get_payment_due_date")
    def test_createOrUpdatePayment_noExistingPayment_newPaymentUpdated(
        self, mock_get_payment_due_date: Mock
    ):
        shares_valid_at = datetime.date(year=2025, month=6, day=3)
        due_date = datetime.date(year=2025, month=6, day=8)
        mock_get_payment_due_date.return_value = due_date
        payment = PaymentFactory.create(
            due_date=due_date + datetime.timedelta(days=1),
            amount=120,
            status=Payment.PaymentStatus.DUE,
            type="Genossenschaftsanteile",
        )
        cache = {}

        result = CoopSharePurchaseHandler.create_or_update_payment(
            shares_valid_at=shares_valid_at,
            mandate_ref=payment.mandate_ref,
            quantity=3,
            cache=cache,
        )

        self.assertNotEqual(payment.id, result.id)
        self.assertEqual(150, result.amount)
        self.assertEqual(2, Payment.objects.count())
