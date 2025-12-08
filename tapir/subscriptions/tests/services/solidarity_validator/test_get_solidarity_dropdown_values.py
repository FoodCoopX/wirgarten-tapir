from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetSolidarityDropdownValues(SimpleTestCase):

    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_getSolidarityDropdownValues_unitIsAbsolute_returnsCorrectValues(
        self, mock_get_parameter_value: Mock
    ):
        parameter_values = {
            ParameterKeys.SOLIDARITY_CHOICES: "-7.5,12",
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        cache = Mock()

        result = SolidarityValidator.get_solidarity_dropdown_values(cache=cache)

        self.assertEqual(
            {
                -7.5: "-7.5€",
                0.0: "Ich möchte den Richtpreis zahlen",
                12.0: "+12€",
                "custom": "Ich möchte einen anderen Betrag zahlen",
            },
            result,
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SOLIDARITY_CHOICES, cache=cache
        )

    def test_getSolidarityDropdownValues_invalidValue_raisesException(self):
        with self.assertRaises(Exception):
            SolidarityValidator.get_solidarity_dropdown_values("-7.5,invalid")

    @patch.object(SolidarityValidator, "get_solidarity_dropdown_values")
    def test_validateSolidarityDropdownValues_getRaisesException_raiseValidationError(
        self, mock_get_solidarity_dropdown_values: Mock
    ):
        mock_get_solidarity_dropdown_values.side_effect = ValueError("Test error")

        with self.assertRaises(ValidationError):
            SolidarityValidator.validate_solidarity_dropdown_values("aaa")

        mock_get_solidarity_dropdown_values.assert_called_once_with("aaa", cache={})

    @patch.object(SolidarityValidator, "get_solidarity_dropdown_values")
    def test_validateSolidarityDropdownValues_getDoesntRaiseException_doNothing(
        self, mock_get_solidarity_dropdown_values: Mock
    ):
        SolidarityValidator.validate_solidarity_dropdown_values("aaa")

        mock_get_solidarity_dropdown_values.assert_called_once_with("aaa", cache={})
