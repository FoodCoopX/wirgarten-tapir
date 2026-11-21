from unittest.mock import patch, MagicMock, call

from tapir.payments.services.pain_008_xml_file_creator import Pain008XmlFileCreator
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlStringGenerator,
    Pain008XmlSinglePaymentException,
)
from tapir.wirgarten.tests.factories import PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildXmlStringWithValidPaymentsAndErrorsForInvalidPayments(TapirUnitTest):
    @patch.object(Pain008XmlStringGenerator, "build_xml_string", autospec=True)
    @patch.object(Pain008XmlStringGenerator, "validate_single_payment", autospec=True)
    def test_buildXmlStringWithValidPaymentsAndErrorsForInvalidPayments_noErrors_buildsStringWithAllPayments(
        self,
        mock_validate_single_payment: MagicMock,
        mock_build_xml_string: MagicMock,
    ):
        all_payments = PaymentFactory.build_batch(size=4)
        collection_date = MagicMock()
        cache = MagicMock()

        mock_build_xml_string.return_value = "test_string"

        xml_string, errors = (
            Pain008XmlFileCreator.build_xml_string_with_valid_payments_and_errors_for_invalid_payments(
                payments=all_payments, collection_date=collection_date, cache=cache
            )
        )

        self.assertEqual("test_string", xml_string)
        self.assertEqual([], errors)

        self.assertEqual(4, mock_validate_single_payment.call_count)
        mock_validate_single_payment.assert_has_calls(
            [
                call(payment=payment, collection_date=collection_date, cache=cache)
                for payment in all_payments
            ],
            any_order=True,
        )
        mock_build_xml_string.assert_called_once_with(
            payments=all_payments,
            collection_date=collection_date,
            cache=cache,
        )

    @patch.object(Pain008XmlStringGenerator, "build_xml_string", autospec=True)
    @patch.object(Pain008XmlStringGenerator, "validate_single_payment", autospec=True)
    def test_buildXmlStringWithValidPaymentsAndErrorsForInvalidPayments_somePaymentsFail_buildsStringWithOnlyValidPaymentsAndReturnsErrorsForInvalidPayments(
        self,
        mock_validate_single_payment: MagicMock,
        mock_build_xml_string: MagicMock,
    ):
        all_payments = PaymentFactory.build_batch(size=4)
        payment_1, payment_2, payment_3, payment_4 = all_payments
        payment_2.id = "the second payment"
        payment_4.id = "the fourth payment"
        failed_payments = {payment_2, payment_4}
        collection_date = MagicMock()
        cache = MagicMock()

        def raise_exception_if_failed_payment(payment, **_):
            if payment in failed_payments:
                raise Pain008XmlSinglePaymentException(f"Error of {payment.id}")

        mock_validate_single_payment.side_effect = raise_exception_if_failed_payment
        mock_build_xml_string.return_value = "test_string"

        xml_string, errors = (
            Pain008XmlFileCreator.build_xml_string_with_valid_payments_and_errors_for_invalid_payments(
                payments=all_payments, collection_date=collection_date, cache=cache
            )
        )

        self.assertEqual("test_string", xml_string)
        self.assertEqual(
            ["Error of the second payment", "Error of the fourth payment"], errors
        )

        self.assertEqual(4, mock_validate_single_payment.call_count)
        mock_validate_single_payment.assert_has_calls(
            [
                call(payment=payment, collection_date=collection_date, cache=cache)
                for payment in all_payments
            ],
            any_order=True,
        )
        mock_build_xml_string.assert_called_once_with(
            payments=[payment_1, payment_3],
            collection_date=collection_date,
            cache=cache,
        )

    @patch.object(Pain008XmlStringGenerator, "build_xml_string", autospec=True)
    @patch.object(Pain008XmlStringGenerator, "validate_single_payment", autospec=True)
    def test_buildXmlStringWithValidPaymentsAndErrorsForInvalidPayments_allPaymentsFail_dontBuildStringAndReturnErrors(
        self,
        mock_validate_single_payment: MagicMock,
        mock_build_xml_string: MagicMock,
    ):
        all_payments = PaymentFactory.build_batch(size=4)
        collection_date = MagicMock()
        cache = MagicMock()

        mock_validate_single_payment.side_effect = Pain008XmlSinglePaymentException(
            "Error"
        )

        xml_string, errors = (
            Pain008XmlFileCreator.build_xml_string_with_valid_payments_and_errors_for_invalid_payments(
                payments=all_payments, collection_date=collection_date, cache=cache
            )
        )

        self.assertEqual(None, xml_string)

        self.assertEqual(4, mock_validate_single_payment.call_count)
        mock_validate_single_payment.assert_has_calls(
            [
                call(payment=payment, collection_date=collection_date, cache=cache)
                for payment in all_payments
            ],
            any_order=True,
        )
        mock_build_xml_string.assert_not_called()
