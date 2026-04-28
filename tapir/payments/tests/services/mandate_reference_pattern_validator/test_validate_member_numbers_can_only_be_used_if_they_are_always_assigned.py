from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateMemberNumbersCanOnlyBeUsedIfTheyAreAlwaysAssigned(TapirUnitTest):
    @patch(
        "tapir.payments.services.mandate_reference_pattern_validator.get_parameter_value"
    )
    def test_validateMemberNumbersCanOnlyBeUsedIfTheyAreAlwaysAssigned_patternHasMemberNumberTokenAndParameterIsTrue_raisesValidationError(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = True

        with self.assertRaises(ValidationError):
            MandateReferencePatternValidator.validate_member_numbers_can_only_be_used_if_they_are_always_assigned(
                "abc-{mitgliedsnummer_kurz}"
            )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, cache={}
        )

    @patch(
        "tapir.payments.services.mandate_reference_pattern_validator.get_parameter_value"
    )
    def test_validateMemberNumbersCanOnlyBeUsedIfTheyAreAlwaysAssigned_patternHasMemberNumberTokenAndParameterIsFalse_noErrorRaised(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = False

        MandateReferencePatternValidator.validate_member_numbers_can_only_be_used_if_they_are_always_assigned(
            "abc-{mitgliedsnummer_lang}"
        )

    @patch(
        "tapir.payments.services.mandate_reference_pattern_validator.get_parameter_value"
    )
    def test_validateMemberNumbersCanOnlyBeUsedIfTheyAreAlwaysAssigned_patternHasNoMemberNumberTokenAndParameterIsTrue_noErrorRaised(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = True

        MandateReferencePatternValidator.validate_member_numbers_can_only_be_used_if_they_are_always_assigned(
            "abc-{zufall}"
        )
