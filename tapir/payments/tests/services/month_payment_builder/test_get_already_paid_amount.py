import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import PaymentFactory, MandateReferenceFactory


class TestGetAlreadyPaidAmount(SimpleTestCase):
    @patch.object(
        TapirCache, "get_payments_by_mandate_ref_and_product_type", autospec=True
    )
    def test_getAlreadyPaidAmount_default_considersOnlyPaymentsThatOverlapWithTheGivenRange(
        self, mock_get_payments_by_mandate_ref_and_product_type: Mock
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
        mock_get_payments_by_mandate_ref_and_product_type.return_value = {
            payment_1,
            payment_2,
            payment_3,
        }

        cache = Mock()
        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
            generated_payments=[],
            cache=cache,
        )

        self.assertEqual(3 + 5, result)
        mock_get_payments_by_mandate_ref_and_product_type.assert_called_once_with(
            mandate_ref=mandate_ref, product_type_name=product_type_name, cache=cache
        )

    @patch.object(
        TapirCache, "get_payments_by_mandate_ref_and_product_type", autospec=True
    )
    def test_getAlreadyPaidAmount_noRelevantPayment_returns0(
        self, mock_get_payments_by_mandate_ref_and_product_type: Mock
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
        mock_get_payments_by_mandate_ref_and_product_type.return_value = {payment}
        cache = Mock()

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
            generated_payments=[],
            cache=cache,
        )

        self.assertEqual(0, result)
        mock_get_payments_by_mandate_ref_and_product_type.assert_called_once_with(
            mandate_ref=mandate_ref, product_type_name=product_type_name, cache=cache
        )

    @patch.object(
        TapirCache, "get_payments_by_mandate_ref_and_product_type", autospec=True
    )
    def test_getAlreadyPaidAmount_generatedPaymentHasOtherMandateRef_generatedPaymentNotCounted(
        self, mock_get_payments_by_mandate_ref_and_product_type: Mock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        mandate_ref_1 = MandateReferenceFactory.build(ref="test_ref1")
        mandate_ref_2 = MandateReferenceFactory.build(ref="test_ref2")
        product_type_name = "product_type_test_name"
        payment = PaymentFactory.build(
            mandate_ref=mandate_ref_2,
            subscription_payment_range_start=datetime.date(year=2028, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2028, month=2, day=19),
            amount=7,
            type=product_type_name,
        )
        mock_get_payments_by_mandate_ref_and_product_type.return_value = set()
        cache = Mock()

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref_1,
            product_type_name=product_type_name,
            generated_payments=[payment],
            cache=cache,
        )

        self.assertEqual(0, result)
        mock_get_payments_by_mandate_ref_and_product_type.assert_called_once_with(
            mandate_ref=mandate_ref_1, product_type_name=product_type_name, cache=cache
        )

    @patch.object(
        TapirCache, "get_payments_by_mandate_ref_and_product_type", autospec=True
    )
    def test_getAlreadyPaidAmount_generatedPaymentHasOtherType_generatedPaymentNotCounted(
        self, mock_get_payments_by_mandate_ref_and_product_type: Mock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        mandate_ref = MandateReferenceFactory.build(ref="test_ref")
        product_type_name = "product_type_test_name"
        payment = PaymentFactory.build(
            mandate_ref=mandate_ref,
            subscription_payment_range_start=datetime.date(year=2028, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2028, month=2, day=19),
            amount=7,
            type="other_type_name",
        )
        mock_get_payments_by_mandate_ref_and_product_type.return_value = set()
        cache = Mock()

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
            generated_payments=[payment],
            cache=cache,
        )

        self.assertEqual(0, result)
        mock_get_payments_by_mandate_ref_and_product_type.assert_called_once_with(
            mandate_ref=mandate_ref, product_type_name=product_type_name, cache=cache
        )

    @patch.object(
        TapirCache, "get_payments_by_mandate_ref_and_product_type", autospec=True
    )
    def test_getAlreadyPaidAmount_generatedPaymentDoesNotOverlapWithRange_generatedPaymentNotCounted(
        self, mock_get_payments_by_mandate_ref_and_product_type: Mock
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
        mock_get_payments_by_mandate_ref_and_product_type.return_value = set()
        cache = Mock()

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
            generated_payments=[payment],
            cache=cache,
        )

        self.assertEqual(0, result)
        mock_get_payments_by_mandate_ref_and_product_type.assert_called_once_with(
            mandate_ref=mandate_ref, product_type_name=product_type_name, cache=cache
        )

    @patch.object(
        TapirCache, "get_payments_by_mandate_ref_and_product_type", autospec=True
    )
    def test_getAlreadyPaidAmount_generatedPaymentIsRelevant_generatedPaymentCounted(
        self, mock_get_payments_by_mandate_ref_and_product_type: Mock
    ):
        range_start = datetime.date(year=2028, month=1, day=1)
        range_end = datetime.date(year=2028, month=1, day=31)
        mandate_ref = MandateReferenceFactory.build(ref="test_ref")
        product_type_name = "product_type_test_name"
        payment = PaymentFactory.build(
            mandate_ref=mandate_ref,
            subscription_payment_range_start=datetime.date(year=2028, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2028, month=2, day=19),
            amount=7,
            type=product_type_name,
        )
        mock_get_payments_by_mandate_ref_and_product_type.return_value = set()
        cache = Mock()

        result = MonthPaymentBuilder.get_already_paid_amount(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name=product_type_name,
            generated_payments=[payment],
            cache=cache,
        )

        self.assertEqual(7, result)
        mock_get_payments_by_mandate_ref_and_product_type.assert_called_once_with(
            mandate_ref=mandate_ref, product_type_name=product_type_name, cache=cache
        )
