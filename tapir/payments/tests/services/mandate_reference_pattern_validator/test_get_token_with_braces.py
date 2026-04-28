from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetTokenWithBraces(TapirUnitTest):
    def test_getTokenWithBraces_default_wrapsTokenInBraces(self):
        result = MandateReferencePatternValidator.get_token_with_braces("vorname")

        self.assertEqual("{vorname}", result)
