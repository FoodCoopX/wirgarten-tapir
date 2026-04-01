from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.deliveries.services.joker_management_service import JokerManagementService


class TestJokerManagementServiceGetExtraJokerRestrictions(SimpleTestCase):
    maxDiff = 1000

    @patch.object(JokerManagementService, "get_extra_joker_restrictions_from_string")
    def test_validateJokerRestrictions_innerFunctionRaisesException_raiseValidationError(
        self, mock_get_extra_joker_restrictions_from_string: Mock
    ):
        mock_get_extra_joker_restrictions_from_string.side_effect = ValueError(
            "test error"
        )

        with self.assertRaises(ValidationError):
            JokerManagementService.validate_joker_restrictions("")

    def test_getExtraJokerRestrictions_restrictionsDisabled_returnsEmptyList(self):
        self.assertEqual(
            [],
            JokerManagementService.get_extra_joker_restrictions_from_string("disabled"),
        )

    def test_getExtraJokerRestrictions_default_returnsCorrectRestrictions(self):
        self.assertEqual(
            [
                JokerManagementService.JokerRestriction(
                    start_day=1, start_month=8, end_day=31, end_month=8, max_jokers=2
                ),
                JokerManagementService.JokerRestriction(
                    start_day=15, start_month=2, end_day=20, end_month=3, max_jokers=3
                ),
            ],
            JokerManagementService.get_extra_joker_restrictions_from_string(
                "01.08.-31.08.[2];15.02.-20.03.[3]"
            ),
        )
