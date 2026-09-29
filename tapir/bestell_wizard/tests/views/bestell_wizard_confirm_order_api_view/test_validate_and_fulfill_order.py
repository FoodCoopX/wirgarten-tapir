from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.bestell_wizard.services.contract_start_date_with_pickup_location import (
    ContractStartDateWithPickupLocation,
)
from tapir.bestell_wizard.views import BestellWizardConfirmOrderApiView


class TestValidateAndFulfillOrder(TapirUnitTest):
    def setUp(self):
        self.validated_serializer_data = {
            "growing_period_id": "test_id",
            "shopping_cart_order": {"product_id": 1},
            "pickup_location_ids": ["pickup_location_id"],
        }
        self.cache = Mock()

    @patch(
        "tapir.bestell_wizard.views.OrderValidator.does_order_need_a_pickup_location",
        return_value=False,
    )
    @patch(
        "tapir.bestell_wizard.views.TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer",
        return_value={},
    )
    @patch.object(
        BestellWizardOrderFulfiller, "create_member_and_fulfill_order", autospec=True
    )
    @patch.object(
        BestellWizardOrderValidator,
        "validate_order_and_user_data_and_distribution_channels",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator,
        "get_growing_period_and_contract_start_date",
        autospec=True,
    )
    def test_validateAndFulfillOrder_orderDoesNotNeedPickupLocation_validatesAndFulfills(
        self,
        mock_get_growing_period_and_contract_start_date: Mock,
        mock_validate_order_and_user_data_and_distribution_channels: Mock,
        mock_create_member_and_fulfill_order: Mock,
        mock_build_tapir_order: Mock,
        mock_does_order_need_a_pickup_location: Mock,
    ):
        request = Mock()
        contract_start_date = Mock()
        mock_get_growing_period_and_contract_start_date.return_value = (
            Mock(),
            contract_start_date,
        )
        member = Mock()
        mock_create_member_and_fulfill_order.return_value = member

        result = BestellWizardConfirmOrderApiView.validate_and_fulfill_order(
            request,
            self.validated_serializer_data,
            cache=self.cache,
        )

        self.assertEqual(member, result)

        mock_get_growing_period_and_contract_start_date.assert_called_once_with(
            growing_period_id="test_id", cache=self.cache
        )
        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order={}, cache=self.cache
        )
        mock_validate_order_and_user_data_and_distribution_channels.assert_called_once_with(
            validated_serializer_data=self.validated_serializer_data,
            contract_start_date=contract_start_date,
            cache=self.cache,
            pickup_location=None,
            order={},
        )
        mock_create_member_and_fulfill_order.assert_called_once_with(
            validated_serializer_data=self.validated_serializer_data,
            contract_start_date=contract_start_date,
            request=request,
            cache=self.cache,
            pickup_location=None,
            order={},
        )

    @patch.object(
        ContractStartDateWithPickupLocation,
        "resolve_contract_start_date_for_pickup_location",
        autospec=True,
    )
    @patch(
        "tapir.bestell_wizard.views.OrderValidator.does_order_need_a_pickup_location",
        return_value=True,
    )
    @patch(
        "tapir.bestell_wizard.views.TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer",
        return_value={},
    )
    @patch.object(
        BestellWizardOrderFulfiller, "create_member_and_fulfill_order", autospec=True
    )
    @patch.object(
        BestellWizardOrderValidator,
        "validate_order_and_user_data_and_distribution_channels",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator,
        "get_growing_period_and_contract_start_date",
        autospec=True,
    )
    def test_validateAndFulfillOrder_pickupLocationStartsInFuture_usesPushedContractStartDate(
        self,
        mock_get_growing_period_and_contract_start_date: Mock,
        mock_validate_order_and_user_data_and_distribution_channels: Mock,
        mock_create_member_and_fulfill_order: Mock,
        mock_build_tapir_order: Mock,
        mock_does_order_need_a_pickup_location: Mock,
        mock_resolve_contract_start_date_for_pickup_location: Mock,
    ):
        request = Mock()
        growing_period = Mock()
        contract_start_date = Mock()
        mock_get_growing_period_and_contract_start_date.return_value = (
            growing_period,
            contract_start_date,
        )
        resolved_pickup_location = Mock()
        adjusted_contract_start_date = Mock()
        mock_resolve_contract_start_date_for_pickup_location.return_value = (
            resolved_pickup_location,
            adjusted_contract_start_date,
        )
        member = Mock()
        mock_create_member_and_fulfill_order.return_value = member

        result = BestellWizardConfirmOrderApiView.validate_and_fulfill_order(
            request,
            self.validated_serializer_data,
            cache=self.cache,
        )

        self.assertEqual(member, result)

        mock_resolve_contract_start_date_for_pickup_location.assert_called_once_with(
            pickup_location_ids=["pickup_location_id"],
            order={},
            contract_start_date=contract_start_date,
            growing_period=growing_period,
            cache=self.cache,
        )
        mock_validate_order_and_user_data_and_distribution_channels.assert_called_once_with(
            validated_serializer_data=self.validated_serializer_data,
            contract_start_date=adjusted_contract_start_date,
            cache=self.cache,
            pickup_location=resolved_pickup_location,
            order={},
        )
        mock_create_member_and_fulfill_order.assert_called_once_with(
            validated_serializer_data=self.validated_serializer_data,
            contract_start_date=adjusted_contract_start_date,
            request=request,
            cache=self.cache,
            pickup_location=resolved_pickup_location,
            order={},
        )

    @patch.object(
        ContractStartDateWithPickupLocation,
        "resolve_contract_start_date_for_pickup_location",
        autospec=True,
    )
    @patch(
        "tapir.bestell_wizard.views.OrderValidator.does_order_need_a_pickup_location",
        return_value=True,
    )
    @patch(
        "tapir.bestell_wizard.views.TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer",
        return_value={},
    )
    @patch.object(
        BestellWizardOrderValidator,
        "validate_order_and_user_data_and_distribution_channels",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator,
        "get_growing_period_and_contract_start_date",
        autospec=True,
    )
    def test_validateAndFulfillOrder_pickupLocationBeyondGrowingPeriod_propagatesValidationError(
        self,
        mock_get_growing_period_and_contract_start_date: Mock,
        mock_validate_order_and_user_data_and_distribution_channels: Mock,
        mock_build_tapir_order: Mock,
        mock_does_order_need_a_pickup_location: Mock,
        mock_resolve_contract_start_date_for_pickup_location: Mock,
    ):
        request = Mock()
        mock_get_growing_period_and_contract_start_date.return_value = (
            Mock(),
            Mock(),
        )
        mock_resolve_contract_start_date_for_pickup_location.side_effect = (
            ValidationError("test error")
        )

        with self.assertRaises(ValidationError):
            BestellWizardConfirmOrderApiView.validate_and_fulfill_order(
                request,
                self.validated_serializer_data,
                cache=self.cache,
            )

        mock_validate_order_and_user_data_and_distribution_channels.assert_not_called()
