import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.models import Payment
from tapir.wirgarten.tests.factories import PaymentFactory, MandateReferenceFactory


class TestGetAlreadyPaidAmount(SimpleTestCase):
    @patch.object(Payment, "objects")
    def test_getAlreadyPaidAmount_default_considersOnlyPaymentsThatOverlapWithTheGivenRange(
        self, mock_payment_objects: Mock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        mandate_ref = MandateReferenceFactory.build(ref="test_ref")
        product_type_name = "product_type_test_name"
        payment_1 = PaymentFactory.build(
            mandate_ref=mandate_ref,
            subscription_payment_range_start=range_start,
            subscription_payment_range_end=range_end,
            amount=3,
            type=product_type_name,
        )
        payment_2 = PaymentFactory.build(
            mandate_ref=mandate_ref,
            subscription_payment_range_start=datetime.date(year=2027, month=12, day=15),
            subscription_payment_range_end=datetime.date(year=2028, month=1, day=19),
            amount=5,
            type=product_type_name,
        )
        payment_3 = PaymentFactory.build(
            mandate_ref=mandate_ref,
            subscription_payment_range_start=datetime.date(year=2028, month=2, day=1),
            subscription_payment_range_end=datetime.date(year=2028, month=2, day=19),
            amount=7,
            type=product_type_name,
        )
        mock_payment_objects.filter.return_value = [payment_1, payment_2, payment_3]

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
        )

        self.assertEqual(3 + 5, result)
        mock_payment_objects.filter.assert_called_once_with(
            mandate_ref=mandate_ref, type=product_type_name
        )

    @patch.object(Payment, "objects")
    def test_getAlreadyPaidAmount_noRelevantPayment_returns0(
        self, mock_payment_objects: Mock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        mandate_ref = MandateReferenceFactory.build(ref="test_ref")
        product_type_name = "product_type_test_name"
        payment = PaymentFactory.build(
            mandate_ref=mandate_ref,
            subscription_payment_range_start=datetime.date(year=2028, month=2, day=1),
            subscription_payment_range_end=datetime.date(year=2028, month=2, day=19),
            amount=7,
            type=product_type_name,
        )
        mock_payment_objects.filter.return_value = [payment]

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
        )

        self.assertEqual(0, result)
        mock_payment_objects.filter.assert_called_once_with(
            mandate_ref=mandate_ref, type=product_type_name
        )
