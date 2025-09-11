from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.bestell_wizard.views import BestellWizardConfirmOrderApiView
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)


class TestValidateAndFulfillOrder(SimpleTestCase):
    @patch(
        "tapir.bestell_wizard.views.get_today",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderFulfiller, "create_member_and_fulfill_order", autospec=True
    )
    @patch.object(
        BestellWizardOrderValidator, "validate_order_and_user_data", autospec=True
    )
    @patch.object(
        ContractStartDateCalculator, "get_next_contract_start_date", autospec=True
    )
    def test_validateAndFulfillOrder_default_validatesThenFulfills(
        self,
        mock_get_next_contract_start_date: Mock,
        mock_validate_order_and_user_data: Mock,
        mock_create_member_and_fulfill_order: Mock,
        mock_get_today: Mock,
    ):
        today = Mock()
        mock_get_today.return_value = today

        request = Mock()
        validated_serializer_data = Mock()
        cache = Mock()

        contract_start_date = Mock()
        mock_get_next_contract_start_date.return_value = contract_start_date

        member = Mock()
        mock_create_member_and_fulfill_order.return_value = member

        result = BestellWizardConfirmOrderApiView.validate_and_fulfill_order(
            request, validated_serializer_data, cache
        )

        self.assertEqual(member, result)

        mock_get_next_contract_start_date.assert_called_once_with(
            reference_date=today, apply_buffer_time=True, cache=cache
        )
        mock_validate_order_and_user_data.assert_called_once_with(
            validated_serializer_data=validated_serializer_data,
            contract_start_date=contract_start_date,
            cache=cache,
        )
        mock_create_member_and_fulfill_order.assert_called_once_with(
            validated_serializer_data=validated_serializer_data,
            contract_start_date=contract_start_date,
            request=request,
            cache=cache,
        )
