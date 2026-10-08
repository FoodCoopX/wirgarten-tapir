from django.core.exceptions import ValidationError

from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidatePhoneNumberIsValid(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.cache = {}

    def set_phone_number_required(self, value: bool):
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED,
            value=value,
        )

    def test_validatePhoneNumberIsValid_validNumber_noError(self):
        self.set_phone_number_required(True)

        PersonalDataValidator.validate_phone_number_is_valid(
            phone_number="017726254738", cache=self.cache
        )

    def test_validatePhoneNumberIsValid_invalidNumber_raisesValidationError(self):
        self.set_phone_number_required(False)

        with self.assertRaises(ValidationError) as error:
            PersonalDataValidator.validate_phone_number_is_valid(
                phone_number="123", cache=self.cache
            )

        self.assertEqual("Ungültige Telefonnummer", error.exception.message)

    def test_validatePhoneNumberIsValid_emptyAndNotRequired_noError(self):
        self.set_phone_number_required(False)

        PersonalDataValidator.validate_phone_number_is_valid(
            phone_number="", cache=self.cache
        )

    def test_validatePhoneNumberIsValid_emptyAndRequired_raisesValidationError(self):
        self.set_phone_number_required(True)

        with self.assertRaises(ValidationError) as error:
            PersonalDataValidator.validate_phone_number_is_valid(
                phone_number="", cache=self.cache
            )

        self.assertEqual("Bitte gib eine Telefonnummer an.", error.exception.message)

    def test_validatePhoneNumberIsValid_onlyWhitespaceAndRequired_raisesValidationError(
        self,
    ):
        self.set_phone_number_required(True)

        with self.assertRaises(ValidationError) as error:
            PersonalDataValidator.validate_phone_number_is_valid(
                phone_number="   ", cache=self.cache
            )

        self.assertEqual("Bitte gib eine Telefonnummer an.", error.exception.message)
