from django.core.exceptions import ValidationError

from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidatePatternDoesntContainsIllegalCharacters(TapirUnitTest):
    def test_validatePatternDoesntContainsIllegalCharacters_onlyAllowedSymbols_doesNotRaise(
        self,
    ):
        MandateReferencePatternValidator.validate_pattern_doesnt_contains_illegal_characters(
            "ABC123+?/-:().,"
        )

    def test_validatePatternDoesntContainsIllegalCharacters_patternIncludesTokens_doesNotRaise(
        self,
    ):
        MandateReferencePatternValidator.validate_pattern_doesnt_contains_illegal_characters(
            "{vorname}{nachname}{mitgliedsnummer_kurz}{zufall}"
        )

    def test_validatePatternDoesntContainsIllegalCharacters_illegalCharacterIncluded_raises(
        self,
    ):
        with self.assertRaises(ValidationError):
            MandateReferencePatternValidator.validate_pattern_doesnt_contains_illegal_characters(
                "abc_def"
            )
