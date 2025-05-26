from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.config import SOLIDARITY_UNIT_PERCENT
from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetSolidarityDropdownValuesAsSortedTuple(SimpleTestCase):
    @patch("tapir.subscriptions.services.solidarity_validator.get_parameter_value")
    def test_getSolidarityDropdownValuesAsSortedTuples_default_returnsCorrectOrder(
        self, mock_get_parameter_value: Mock
    ):
        parameter_values = {
            ParameterKeys.SOLIDARITY_UNIT: SOLIDARITY_UNIT_PERCENT,
            ParameterKeys.SOLIDARITY_CHOICES: "5,-7,2",
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        cache = Mock()

        result = SolidarityValidator.get_solidarity_dropdown_value_as_sorted_tuples(
            cache=cache
        )

        self.assertEqual(
            [
                (0.0, "Ich möchte den Richtpreis zahlen"),
                (5.0, "+5%"),
                (2.0, "+2%"),
                (-7.0, "-7%"),
                ("custom", "Ich möchte einen anderen Betrag zahlen  ⟶"),
            ],
            result,
        )
