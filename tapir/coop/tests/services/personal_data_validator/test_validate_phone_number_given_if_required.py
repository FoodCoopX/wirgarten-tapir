from django.core.exceptions import ValidationError

from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidatePhoneNumberGivenIfRequired(TapirUnitTest):
    def test_validatePhoneNumberGivenIfRequired_numberGivenAndRequired_noError(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, value=True
        )

        PersonalDataValidator.validate_phone_number_given_if_required(
            phone_number="+49 30 1234567", cache=cache
        )

    def test_validatePhoneNumberGivenIfRequired_numberEmptyAndNotRequired_noError(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, value=False
        )

        PersonalDataValidator.validate_phone_number_given_if_required(
            phone_number="", cache=cache
        )

    def test_validatePhoneNumberGivenIfRequired_numberEmptyAndRequired_raisesValidationError(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, value=True
        )

        with self.assertRaises(ValidationError) as error:
            PersonalDataValidator.validate_phone_number_given_if_required(
                phone_number="", cache=cache
            )

        self.assertEqual("Bitte gib eine Telefonnummer an.", error.exception.message)

    def test_validatePhoneNumberGivenIfRequired_numberOnlyWhitespaceAndRequired_raisesValidationError(
        self,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, value=True
        )

        with self.assertRaises(ValidationError):
            PersonalDataValidator.validate_phone_number_given_if_required(
                phone_number="   ", cache=cache
            )
