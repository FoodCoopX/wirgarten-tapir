from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)


class TestSubscriptionUpdateViewValidatorValidateEverything(TapirUnitTest):
    def build_default_params(self):
        self.mock_order = Mock()
        self.mock_product_type = Mock()
        self.mock_contract_start_date = Mock()
        self.mock_member = Mock()
        self.mock_cache = Mock()

        return {
            "sepa_allowed": True,
            "cancellation_policy_read": True,
            "order": self.mock_order,
            "product_type": self.mock_product_type,
            "contract_start_date": self.mock_contract_start_date,
            "member": self.mock_member,
            "logged_in_user_is_admin": False,
            "desired_pickup_location_id": "test_pickup_location_id",
            "account_owner": "test_account_owner",
            "iban": "test_iban",
            "payment_rhythm": "test_payment_rhythm",
            "cache": self.mock_cache,
        }

    def test_validateEverything_sepaNotAllowed_raisesValidationError(self):
        params = self.build_default_params()
        params["sepa_allowed"] = False

        with self.assertRaises(ValidationError):
            SubscriptionUpdateViewValidator.validate_everything(**params)

    def test_validateEverything_cancellationPolicyNotRead_raisesValidationError(self):
        params = self.build_default_params()
        params["cancellation_policy_read"] = False

        with self.assertRaises(ValidationError):
            SubscriptionUpdateViewValidator.validate_everything(**params)

    @patch.object(
        SubscriptionUpdateViewValidator,
        "validate_additional_product_can_be_ordered_without_base_product_subscription",
        autospec=True,
    )
    @patch.object(OrderValidator, "validate_at_least_one_change", autospec=True)
    @patch.object(OrderValidator, "validate_cannot_reduce_size", autospec=True)
    @patch.object(OrderValidator, "validate_order_general", autospec=True)
    @patch.object(
        SubscriptionUpdateViewValidator, "validate_pickup_location", autospec=True
    )
    @patch.object(
        SubscriptionUpdateViewValidator,
        "validate_all_products_belong_to_product_type",
        autospec=True,
    )
    @patch.object(
        SubscriptionUpdateViewValidator, "validate_banking_data", autospec=True
    )
    def test_validateEverything_allValid_callsAllValidators(
        self,
        mock_validate_banking_data: Mock,
        mock_validate_all_products_belong_to_product_type: Mock,
        mock_validate_pickup_location: Mock,
        mock_validate_order_general: Mock,
        mock_validate_cannot_reduce_size: Mock,
        mock_validate_at_least_one_change: Mock,
        mock_validate_additional_product_can_be_ordered_without_base_product_subscription: Mock,
    ):
        mock_pickup_location = Mock()
        mock_validate_pickup_location.return_value = mock_pickup_location
        params = self.build_default_params()

        SubscriptionUpdateViewValidator.validate_everything(**params)

        mock_validate_all_products_belong_to_product_type.assert_called_once_with(
            order=self.mock_order,
            product_type_id=self.mock_product_type.id,
            cache=self.mock_cache,
        )
        mock_validate_pickup_location.assert_called_once_with(
            order=self.mock_order,
            desired_pickup_location_id="test_pickup_location_id",
            contract_start_date=self.mock_contract_start_date,
            member=self.mock_member,
            cache=self.mock_cache,
        )
        mock_validate_order_general.assert_called_once_with(
            order=self.mock_order,
            pickup_location=mock_pickup_location,
            contract_start_date=self.mock_contract_start_date,
            cache=self.mock_cache,
            member=self.mock_member,
        )
        mock_validate_cannot_reduce_size.assert_called_once_with(
            logged_in_user_is_admin=False,
            contract_start_date=self.mock_contract_start_date,
            member=self.mock_member,
            order_for_a_single_product_type=self.mock_order,
            product_type=self.mock_product_type,
            cache=self.mock_cache,
        )
        mock_validate_at_least_one_change.assert_called_once_with(
            member=self.mock_member,
            contract_start_date=self.mock_contract_start_date,
            cache=self.mock_cache,
            product_type=self.mock_product_type,
            order=self.mock_order,
        )
        mock_validate_additional_product_can_be_ordered_without_base_product_subscription.assert_called_once_with(
            product_type=self.mock_product_type,
            member=self.mock_member,
            contract_start_date=self.mock_contract_start_date,
            cache=self.mock_cache,
        )
        mock_validate_banking_data.assert_called_once_with(
            member=self.mock_member,
            account_owner="test_account_owner",
            iban="test_iban",
            payment_rhythm="test_payment_rhythm",
            cache=self.mock_cache,
        )
