from unittest.mock import Mock, patch, call

from django.core.exceptions import ValidationError

from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestApplyReplacementsForLine(TapirUnitTest):
    @patch.object(
        IntendedUsePatternExpander,
        "_apply_replacements_for_line_with_max_length",
        autospec=True,
    )
    def test_applyReplacementsForLine_firstAttemptFitsInMaxLength_returnsResultAndCallsInnerOnce(
        self, mock_apply_replacements_for_line_with_max_length: Mock
    ):
        mock_apply_replacements_for_line_with_max_length.return_value = "short result"
        replacements = Mock()
        token_value_overrides = Mock()

        result = IntendedUsePatternExpander._apply_replacements_for_line(
            line="Hi {vorname}",
            replacements=replacements,
            token_value_overrides=token_value_overrides,
        )

        self.assertEqual("short result", result)
        mock_apply_replacements_for_line_with_max_length.assert_called_once_with(
            line="Hi {vorname}",
            replacements=replacements,
            max_length=IntendedUsePatternExpander.MAX_LENGTH_PER_LINE,
            token_value_overrides=token_value_overrides,
        )

    @patch.object(
        IntendedUsePatternExpander,
        "_apply_replacements_for_line_with_max_length",
        autospec=True,
    )
    def test_applyReplacementsForLine_secondAttemptFitsInMaxLength_returnsSecondResultAndCallsInnerTwice(
        self, mock_apply_replacements_for_line_with_max_length: Mock
    ):
        too_long_1 = "x" * (IntendedUsePatternExpander.MAX_LENGTH_PER_LINE + 2)
        too_long_2 = "x" * (IntendedUsePatternExpander.MAX_LENGTH_PER_LINE + 1)
        fits = "x" * IntendedUsePatternExpander.MAX_LENGTH_PER_LINE
        mock_apply_replacements_for_line_with_max_length.side_effect = [
            too_long_1,
            too_long_2,
            fits,
        ]
        replacements = Mock()
        token_value_overrides = Mock()

        result = IntendedUsePatternExpander._apply_replacements_for_line(
            line="line",
            replacements=replacements,
            token_value_overrides=token_value_overrides,
        )

        self.assertEqual(fits, result)
        self.assertEqual(3, mock_apply_replacements_for_line_with_max_length.call_count)
        mock_apply_replacements_for_line_with_max_length.assert_has_calls(
            [
                call(
                    line="line",
                    replacements=replacements,
                    max_length=IntendedUsePatternExpander.MAX_LENGTH_PER_LINE - index,
                    token_value_overrides=token_value_overrides,
                )
                for index in range(3)
            ],
            any_order=False,
        )

    @patch.object(
        IntendedUsePatternExpander,
        "_apply_replacements_for_line_with_max_length",
        autospec=True,
    )
    def test_applyReplacementsForLine_allAttemptsExceedMaxLength_raisesValidationErrorMentioningLine(
        self, mock_apply_replacements_for_line_with_max_length: Mock
    ):
        too_long = "x" * (IntendedUsePatternExpander.MAX_LENGTH_PER_LINE + 1)
        mock_apply_replacements_for_line_with_max_length.return_value = too_long
        line = "line that never fits"

        with self.assertRaises(ValidationError) as context:
            IntendedUsePatternExpander._apply_replacements_for_line(
                line=line,
                replacements={},
                token_value_overrides={},
            )

        self.assertEqual(
            "Diese Zeile: 'line that never fits' ist zu lang wenn die Tokens expandiert sind.",
            context.exception.message,
        )
