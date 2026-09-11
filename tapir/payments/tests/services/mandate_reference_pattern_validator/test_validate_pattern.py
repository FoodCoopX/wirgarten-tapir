from unittest.mock import patch, Mock

from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidatePattern(TapirUnitTest):
    @patch.object(
        MandateReferencePatternValidator,
        "validate_pattern_doesnt_contains_illegal_characters",
    )
    @patch.object(
        MandateReferencePatternValidator,
        "validate_member_numbers_can_only_be_used_if_they_are_always_assigned",
    )
    @patch.object(
        MandateReferencePatternValidator,
        "validate_pattern_contains_at_least_one_unique_token",
    )
    def test_validatePattern_default_callsAllSubValidators(
        self,
        mock_validate_pattern_contains_at_least_one_unique_token: Mock,
        mock_validate_member_numbers_can_only_be_used_if_they_are_always_assigned: Mock,
        mock_validate_pattern_doesnt_contains_illegal_characters: Mock,
    ):
        pattern = Mock()

        MandateReferencePatternValidator.validate_pattern(pattern)

        mock_validate_pattern_contains_at_least_one_unique_token.assert_called_once_with(
            pattern
        )
        mock_validate_member_numbers_can_only_be_used_if_they_are_always_assigned.assert_called_once_with(
            pattern
        )
        mock_validate_pattern_doesnt_contains_illegal_characters.assert_called_once_with(
            pattern
        )
