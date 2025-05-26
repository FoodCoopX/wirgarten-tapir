from unittest.mock import Mock, patch, call

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
    SOLIDARITY_MODE_ONLY_POSITIVE,
    SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
    SOLIDARITY_UNIT_ABSOLUTE,
    SOLIDARITY_UNIT_PERCENT,
)
from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestValidateSolidarityPrice(SimpleTestCase):
    def test_validateSolidarityPrice_noSolidarityPriceGiven_noErrorRaised(self):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": None,
            "solidarity_price_absolute": None,
        }

        SolidarityValidator.validate_solidarity_price(
            form=form, start_date=Mock(), field_prefix=Mock(), cache=Mock()
        )

    def test_validateSolidarityPrice_positivePercentage_noErrorRaised(self):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": 1,
            "solidarity_price_absolute": None,
        }

        SolidarityValidator.validate_solidarity_price(
            form=form, start_date=Mock(), field_prefix=Mock(), cache=Mock()
        )

    def test_validateSolidarityPrice_positiveAbsoluteValue_noErrorRaised(self):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": None,
            "solidarity_price_absolute": 1,
        }

        SolidarityValidator.validate_solidarity_price(
            form=form, start_date=Mock(), field_prefix=Mock(), cache=Mock()
        )

    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_validateSolidarityPrice_modeIsNegativeAlwaysAllowed_noErrorRaised(
        self, mock_get_parameter_value: Mock
    ):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": -100000,
            "solidarity_price_absolute": None,
        }

        mock_get_parameter_value.return_value = SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED
        cache = Mock()

        SolidarityValidator.validate_solidarity_price(
            form=form, start_date=Mock(), field_prefix=Mock(), cache=cache
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )

    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_validateSolidarityPrice_modeIsOnlyPositiveAllowedAndSendingNegativeValue_validationErrorRaised(
        self, mock_get_parameter_value: Mock
    ):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": -1,
            "solidarity_price_absolute": None,
        }

        mock_get_parameter_value.return_value = SOLIDARITY_MODE_ONLY_POSITIVE
        cache = Mock()

        with self.assertRaises(ValidationError):
            SolidarityValidator.validate_solidarity_price(
                form=form, start_date=Mock(), field_prefix=Mock(), cache=cache
            )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess")
    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_validateSolidarityPrice_modeIsAutoAndUnitIsAbsoluteAndEnoughSoli_noErrorRaised(
        self, mock_get_parameter_value: Mock, mock_get_solidarity_excess: Mock
    ):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": None,
            "solidarity_price_absolute": -10,
        }

        parameter_values = {
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED: SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
            ParameterKeys.SOLIDARITY_UNIT: SOLIDARITY_UNIT_ABSOLUTE,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        mock_get_solidarity_excess.return_value = 10

        cache = Mock()
        start_date = Mock()
        field_prefix = "test_field_prefix"

        SolidarityValidator.validate_solidarity_price(
            form=form, start_date=start_date, field_prefix=field_prefix, cache=cache
        )

        mock_get_parameter_value.assert_has_calls(
            [
                call(ParameterKeys.SOLIDARITY_UNIT, cache=cache),
                call(ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache),
            ],
            any_order=True,
        )

    @patch.object(SolidarityValidator, "get_solidarity_excess")
    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_validateSolidarityPrice_modeIsAutoAndUnitIsAbsoluteAndNotEnoughSoli_raisesValidationError(
        self, mock_get_parameter_value: Mock, mock_get_solidarity_excess: Mock
    ):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": None,
            "solidarity_price_absolute": -10,
        }

        parameter_values = {
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED: SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
            ParameterKeys.SOLIDARITY_UNIT: SOLIDARITY_UNIT_ABSOLUTE,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        mock_get_solidarity_excess.return_value = 5

        cache = Mock()
        start_date = Mock()
        field_prefix = "test_field_prefix"

        with self.assertRaises(ValidationError):
            SolidarityValidator.validate_solidarity_price(
                form=form, start_date=start_date, field_prefix=field_prefix, cache=cache
            )

        mock_get_parameter_value.assert_has_calls(
            [
                call(ParameterKeys.SOLIDARITY_UNIT, cache=cache),
                call(ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache),
            ],
            any_order=True,
        )

    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess")
    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_validateSolidarityPrice_modeIsAutoAndUnitIsPercentageAndEnoughSoli_noErrorRaised(
        self,
        mock_get_parameter_value: Mock,
        mock_get_solidarity_excess: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": -0.1,
            "solidarity_price_absolute": None,
        }

        parameter_values = {
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED: SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
            ParameterKeys.SOLIDARITY_UNIT: SOLIDARITY_UNIT_PERCENT,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        mock_get_solidarity_excess.return_value = 6
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 60

        cache = Mock()
        start_date = Mock()
        field_prefix = "test_field_prefix"

        SolidarityValidator.validate_solidarity_price(
            form=form, start_date=start_date, field_prefix=field_prefix, cache=cache
        )

        mock_get_parameter_value.assert_has_calls(
            [
                call(ParameterKeys.SOLIDARITY_UNIT, cache=cache),
                call(ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache),
            ],
            any_order=True,
        )

    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    @patch.object(SolidarityValidator, "get_solidarity_excess")
    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_validateSolidarityPrice_modeIsAutoAndUnitIsPercentageAndNotEnoughSoli_raisesValidationError(
        self,
        mock_get_parameter_value: Mock,
        mock_get_solidarity_excess: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        form = Mock()
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": -0.1,
            "solidarity_price_absolute": None,
        }

        parameter_values = {
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED: SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
            ParameterKeys.SOLIDARITY_UNIT: SOLIDARITY_UNIT_PERCENT,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        mock_get_solidarity_excess.return_value = 5
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 60

        cache = Mock()
        start_date = Mock()
        field_prefix = "test_field_prefix"

        with self.assertRaises(ValidationError):
            SolidarityValidator.validate_solidarity_price(
                form=form, start_date=start_date, field_prefix=field_prefix, cache=cache
            )

        mock_get_parameter_value.assert_has_calls(
            [
                call(ParameterKeys.SOLIDARITY_UNIT, cache=cache),
                call(ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache),
            ],
            any_order=True,
        )
