from unittest.mock import patch, Mock

from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.bestell_wizard.views import BestellWizardConfirmOrderApiView
from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddressInput,
)


class TestValidateAndFulfillOrder(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.deposit_validation = self.enterContext(
            patch.object(
                AssociationDepositPolicy, "validate_signup_selection", autospec=True
            )
        )

    @patch.object(
        BestellWizardOrderValidator, "validate_home_delivery_address", autospec=True
    )
    @patch.object(
        BestellWizardConfirmOrderApiView, "build_delivery_address_input", autospec=True
    )
    @patch(
        "tapir.bestell_wizard.views.get_today",
        autospec=True,
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
        "validated_growing_period_and_get_contract_start_date",
        autospec=True,
    )
    def test_validateAndFulfillOrder_default_validatesThenFulfills(
        self,
        mock_validated_growing_period_and_get_contract_start_date: Mock,
        mock_validate_order_and_user_data_and_distribution_channels: Mock,
        mock_create_member_and_fulfill_order: Mock,
        mock_get_today: Mock,
        mock_build_delivery_address_input: Mock,
        mock_validate_home_delivery_address: Mock,
    ):
        today = Mock()
        mock_get_today.return_value = today

        request = Mock()
        validated_serializer_data = {
            "growing_period_id": "test_id",
            "pickup_location_ids": ["test_pickup_location_id"],
            "personal_data": {"first_name": "John"},
            "shopping_cart_order": {"product": 1},
        }
        cache = Mock()

        contract_start_date = Mock()
        mock_validated_growing_period_and_get_contract_start_date.return_value = (
            contract_start_date
        )

        member = Mock()
        mock_create_member_and_fulfill_order.return_value = member
        delivery_address_input = DeliveryAddressInput(
            same_as_billing_address=True,
            street="",
            street_2="",
            postcode="",
            city="",
            country="",
        )
        mock_build_delivery_address_input.return_value = delivery_address_input

        result = BestellWizardConfirmOrderApiView.validate_and_fulfill_order(
            request,
            validated_serializer_data,
            cache=cache,
        )

        self.assertEqual(member, result)
        self.deposit_validation.assert_called_once_with(
            None, True, cache, payment_option="once"
        )

        mock_validated_growing_period_and_get_contract_start_date.assert_called_once_with(
            "test_id", cache=cache
        )
        mock_validate_order_and_user_data_and_distribution_channels.assert_called_once_with(
            validated_serializer_data=validated_serializer_data,
            contract_start_date=contract_start_date,
            cache=cache,
        )
        mock_build_delivery_address_input.assert_called_once_with(
            validated_serializer_data=validated_serializer_data
        )
        mock_validate_home_delivery_address.assert_called_once_with(
            pickup_location_ids=["test_pickup_location_id"],
            delivery_address_input=delivery_address_input,
            personal_data={"first_name": "John"},
            cache=cache,
        )
        mock_create_member_and_fulfill_order.assert_called_once_with(
            validated_serializer_data=validated_serializer_data,
            delivery_address_input=delivery_address_input,
            contract_start_date=contract_start_date,
            request=request,
            cache=cache,
        )
