from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.config import SOLIDARITY_UNIT_PERCENT, SOLIDARITY_UNIT_ABSOLUTE
from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetSolidarityDropdownValues(SimpleTestCase):
    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_getSolidarityDropdownValues_unitIsPercentage_returnsCorrectPercentages(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = SOLIDARITY_UNIT_PERCENT
        cache = Mock()

        result = SolidarityValidator.get_solidarity_dropdown_values(
            "-5,0,5", cache=cache
        )

        self.assertEqual(
            {
                -5.0: "-5%",
                0.0: "Ich möchte den Richtpreis zahlen",
                5.0: "+5%",
                "custom": "Ich möchte einen anderen Betrag zahlen  ⟶",
            },
            result,
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SOLIDARITY_UNIT, cache=cache
        )

    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_getSolidarityDropdownValues_unitIsAbsolute_returnsCorrectValues(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = SOLIDARITY_UNIT_ABSOLUTE
        cache = Mock()

        result = SolidarityValidator.get_solidarity_dropdown_values(
            "-7.5,12", cache=cache
        )

        self.assertEqual(
            {
                -7.5: "-7.5€",
                0.0: "Ich möchte den Richtpreis zahlen",
                12.0: "+12€",
                "custom": "Ich möchte einen anderen Betrag zahlen  ⟶",
            },
            result,
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SOLIDARITY_UNIT, cache=cache
        )

    def test_getSolidarityDropdownValues_invalidValue_raisesException(self):
        with self.assertRaises(Exception):
            SolidarityValidator.get_solidarity_dropdown_values("-7.5,invalid", cache={})
