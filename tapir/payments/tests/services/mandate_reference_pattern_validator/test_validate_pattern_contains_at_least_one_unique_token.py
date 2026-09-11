from django.core.exceptions import ValidationError

from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidatePatternContainsAtLeastOneUniqueToken(TapirUnitTest):
    def test_validatePatternContainsAtLeastOneUniqueToken_patternRandomToken_doesNotRaise(
        self,
    ):
        MandateReferencePatternValidator.validate_pattern_contains_at_least_one_unique_token(
            "abc-{zufall}"
        )

    def test_validatePatternContainsAtLeastOneUniqueToken_patternAMemberNumberToken_doesNotRaise(
        self,
    ):
        MandateReferencePatternValidator.validate_pattern_contains_at_least_one_unique_token(
            "abc-{mitgliedsnummer_kurz}"
        )

    def test_validatePatternContainsAtLeastOneUniqueToken_patternHasOnlyNonUniqueTokens_raises(
        self,
    ):
        with self.assertRaises(ValidationError):
            MandateReferencePatternValidator.validate_pattern_contains_at_least_one_unique_token(
                "{vorname}-{nachname}"
            )
