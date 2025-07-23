import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetPaymentDueDate(SimpleTestCase):
    @patch("tapir.coop.services.coop_share_purchase_handler.get_parameter_value")
    def test_getPaymentDueDate_sharesValidBeforePaymentDueDayOfMonth_returnsDateInSameMonth(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = 12
        shares_valid_at = datetime.date(2024, 8, 6)
        cache = Mock()

        result = CoopSharePurchaseHandler.get_payment_due_date(
            shares_valid_at=shares_valid_at, cache=cache
        )

        self.assertEqual(result, datetime.date(2024, 8, 12))
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.PAYMENT_DUE_DAY, cache=cache
        )

    @patch("tapir.coop.services.coop_share_purchase_handler.get_parameter_value")
    def test_getPaymentDueDate_sharesValidAfterPaymentDueDayOfMonth_returnsDateInFollowingMonth(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = 12
        shares_valid_at = datetime.date(2024, 8, 13)
        cache = Mock()

        result = CoopSharePurchaseHandler.get_payment_due_date(
            shares_valid_at=shares_valid_at, cache=cache
        )

        self.assertEqual(result, datetime.date(2024, 9, 12))
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.PAYMENT_DUE_DAY, cache=cache
        )

    @patch("tapir.coop.services.coop_share_purchase_handler.get_parameter_value")
    def test_getPaymentDueDate_sharesValidOnPaymentDueDayOfMonth_returnsDateInSameMonth(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = 12
        shares_valid_at = datetime.date(2024, 8, 12)
        cache = Mock()

        result = CoopSharePurchaseHandler.get_payment_due_date(
            shares_valid_at=shares_valid_at, cache=cache
        )

        self.assertEqual(result, datetime.date(2024, 8, 12))
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.PAYMENT_DUE_DAY, cache=cache
        )
