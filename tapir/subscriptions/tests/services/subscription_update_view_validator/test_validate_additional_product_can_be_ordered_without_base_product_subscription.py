from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


@patch(
    "tapir.subscriptions.services.subscription_update_view_validator.get_active_and_future_subscriptions",
    autospec=True,
)
@patch.object(BaseProductTypeService, "get_base_product_type", autospec=True)
class TestSubscriptionUpdateViewValidatorValidateAdditionalProductCanBeOrderedWithoutBaseProductSubscription(
    SimpleTestCase,
):
    def build_default_params(self):
        self.product_type = Mock()
        self.member = Mock()
        self.contract_start_date = Mock()
        self.cache = {}
        return {
            "product_type": self.product_type,
            "member": self.member,
            "contract_start_date": self.contract_start_date,
            "cache": self.cache,
        }

    def test_validateAdditionalProductCanBeOrderedWithoutBaseProductSubscription_parameterAllowsAdditionalProductWithoutBase_noErrorRaised(
        self,
        mock_get_base_product_type: Mock,
        mock_get_active_and_future_subscriptions: Mock,
    ):
        params = self.build_default_params()
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            value=True,
        )

        SubscriptionUpdateViewValidator.validate_additional_product_can_be_ordered_without_base_product_subscription(
            **params
        )

        mock_get_base_product_type.assert_not_called()
        mock_get_active_and_future_subscriptions.assert_not_called()

    def test_validateAdditionalProductCanBeOrderedWithoutBaseProductSubscription_productTypeIsBaseProductType_returns(
        self,
        mock_get_base_product_type: Mock,
        mock_get_active_and_future_subscriptions: Mock,
    ):
        params = self.build_default_params()
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            value=False,
        )
        mock_get_base_product_type.return_value = self.product_type

        SubscriptionUpdateViewValidator.validate_additional_product_can_be_ordered_without_base_product_subscription(
            **params
        )

        mock_get_base_product_type.assert_called_once_with(cache=self.cache)
        mock_get_active_and_future_subscriptions.assert_not_called()

    def test_validateAdditionalProductCanBeOrderedWithoutBaseProductSubscription_memberHasSubscriptionToBaseProductType_returns(
        self,
        mock_get_base_product_type: Mock,
        mock_get_active_and_future_subscriptions: Mock,
    ):
        params = self.build_default_params()
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            value=False,
        )

        mock_base_product_type = Mock()
        mock_get_base_product_type.return_value = mock_base_product_type
        mock_all_subscriptions_queryset = Mock()
        mock_get_active_and_future_subscriptions.return_value = (
            mock_all_subscriptions_queryset
        )
        mock_filtered_queryset = Mock()
        mock_all_subscriptions_queryset.filter.return_value = mock_filtered_queryset
        mock_filtered_queryset.exists.return_value = True

        SubscriptionUpdateViewValidator.validate_additional_product_can_be_ordered_without_base_product_subscription(
            **params
        )

        mock_get_base_product_type.assert_called_once_with(cache=self.cache)
        mock_get_active_and_future_subscriptions.assert_called_once_with(
            reference_date=self.contract_start_date
        )
        mock_all_subscriptions_queryset.filter.assert_called_once_with(
            member__id=self.member.id,
            product__type__id=mock_base_product_type.id,
        )
        mock_filtered_queryset.exists.assert_called_once_with()

    def test_validateAdditionalProductCanBeOrderedWithoutBaseProductSubscription_memberDoesNotHaveSubscriptionToBaseProductType_raisesValidationError(
        self,
        mock_get_base_product_type: Mock,
        mock_get_active_and_future_subscriptions: Mock,
    ):
        params = self.build_default_params()
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            value=False,
        )

        mock_base_product_type = Mock()
        mock_get_base_product_type.return_value = mock_base_product_type
        mock_all_subscriptions_queryset = Mock()
        mock_get_active_and_future_subscriptions.return_value = (
            mock_all_subscriptions_queryset
        )
        mock_filtered_queryset = Mock()
        mock_all_subscriptions_queryset.filter.return_value = mock_filtered_queryset
        mock_filtered_queryset.exists.return_value = False

        with self.assertRaises(ValidationError) as error:
            SubscriptionUpdateViewValidator.validate_additional_product_can_be_ordered_without_base_product_subscription(
                **params
            )

        self.assertEqual(
            "Um Anteile von diese zusätzliche Produkte zu bestellen, "
            "musst du Anteile von der Basis-Produkt an der gleiche Vertragsperiode haben.",
            error.exception.message,
        )

        mock_get_base_product_type.assert_called_once_with(cache=self.cache)
        mock_get_active_and_future_subscriptions.assert_called_once_with(
            reference_date=self.contract_start_date
        )
        mock_all_subscriptions_queryset.filter.assert_called_once_with(
            member__id=self.member.id,
            product__type__id=mock_base_product_type.id,
        )
        mock_filtered_queryset.exists.assert_called_once_with()
