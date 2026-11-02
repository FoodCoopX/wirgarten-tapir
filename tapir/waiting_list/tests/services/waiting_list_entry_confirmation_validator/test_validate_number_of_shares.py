from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError

from tapir.coop.services.coop_share_instalment_order_validator import (
    CoopShareInstalmentOrderValidator,
)
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
                order=order,
                desired_number_of_coop_shares=3,
                pay_in_instalments=False,
                cache=cache,
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
            order=order,
            desired_number_of_coop_shares=4,
            pay_in_instalments=False,
            cache=cache,
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
            order=order,
            desired_number_of_coop_shares=5,
            pay_in_instalments=False,
            cache=cache,
        )

    @patch.object(
        CoopShareInstalmentOrderValidator, "validate_instalments", autospec=True
    )
    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    def test_validateNumberOfShares_payInInstalments_validatesInstalments(
        self,
        mock_get_minimum_number_of_shares_for_tapir_order: Mock,
        mock_validate_instalments: Mock,
    ):
        cache = Mock()
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 4

        WaitingListEntryConfirmationValidator.validate_number_of_shares(
            order=Mock(),
            desired_number_of_coop_shares=4,
            pay_in_instalments=True,
            cache=cache,
        )

        mock_validate_instalments.assert_called_once_with(
            number_of_coop_shares=4, minimum_number_of_coop_shares=4, cache=cache
        )
