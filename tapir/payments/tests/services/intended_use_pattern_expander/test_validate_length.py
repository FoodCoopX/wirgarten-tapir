from django.core.exceptions import ValidationError

from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateLength(TapirUnitTest):
    def test_validateLength_exactlyMaxLength_noError(self):
        IntendedUsePatternExpander._validate_length(
            "x" * IntendedUsePatternExpander.MAX_LENGTH
        )

    def test_validateLength_longerThanMaxLength_raisesValidationError(self):
        with self.assertRaises(ValidationError) as context:
            IntendedUsePatternExpander._validate_length(
                "x" * (IntendedUsePatternExpander.MAX_LENGTH + 1)
            )

        self.assertEqual(
            f"Der Verwendungszweck ist zu lang (141 Zeichen, maximal 140): '{"x" * 141}'",
            context.exception.message,
        )

    def test_validateLength_specialCharactersExpandBeyondMaxLength_raisesValidationError(
        self,
    ):
        intended_use = "x" * (IntendedUsePatternExpander.MAX_LENGTH - 1) + "ö"

        with self.assertRaises(ValidationError):
            IntendedUsePatternExpander._validate_length(intended_use)

    def test_validateLength_multipleLines_newlinesCountAsSingleSpace(self):
        half = "x" * 70

        IntendedUsePatternExpander._validate_length(f"{half}\n{"x" * 69}")
