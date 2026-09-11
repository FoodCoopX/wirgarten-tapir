from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError

from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateNumberOfShares(TapirUnitTest):
    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    def test_validateNumberOfShares_givenNumberIsLessThanMinimum_raisesValidationError(
        self, mock_get_minimum_number_of_shares_for_tapir_order: Mock
    ):
        order = Mock()
        cache = Mock()
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 4

        with self.assertRaises(ValidationError) as error_context:
            WaitingListEntryConfirmationValidator.validate_number_of_shares(
                order=order, desired_number_of_coop_shares=3, cache=cache
            )

        mock_get_minimum_number_of_shares_for_tapir_order.assert_called_once_with(
            order=order, cache=cache
        )
        self.assertEqual(
            "Diese Bestellung erfordert mindestens 4 Genossenschaftsanteile",
            error_context.exception.message,
        )

    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    def test_validateNumberOfShares_givenNumberIsEqualToMinimum_doesNothing(
        self, mock_get_minimum_number_of_shares_for_tapir_order: Mock
    ):
        order = Mock()
        cache = Mock()
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 4

        WaitingListEntryConfirmationValidator.validate_number_of_shares(
            order=order, desired_number_of_coop_shares=4, cache=cache
        )

    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    def test_validateNumberOfShares_givenNumberIsMoreThanMinimum_doesNothing(
        self, mock_get_minimum_number_of_shares_for_tapir_order: Mock
    ):
        order = Mock()
        cache = Mock()
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 4

        WaitingListEntryConfirmationValidator.validate_number_of_shares(
            order=order, desired_number_of_coop_shares=5, cache=cache
        )
