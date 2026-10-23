from django.core.exceptions import ValidationError

from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.wirgarten.validators import validate_optional_url


class TestValidateOptionalUrl(TapirUnitTest):
    def test_validateOptionalUrl_emptyString_noError(self):
        validate_optional_url("")

    def test_validateOptionalUrl_validUrl_noError(self):
        validate_optional_url("https://lueneburg.wirgarten.com")

    def test_validateOptionalUrl_invalidUrl_raisesValidationError(self):
        with self.assertRaises(ValidationError):
            validate_optional_url("keine-url")
