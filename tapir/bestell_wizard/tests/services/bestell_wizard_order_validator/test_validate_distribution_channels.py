from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.bestell_wizard.services.questionnaire_source_service import (
    QuestionnaireSourceService,
)


class TestValidateDistributionChannels(SimpleTestCase):
    @patch.object(
        QuestionnaireSourceService, "get_questionnaire_source_choices", autospec=True
    )
    def test_validateDistributionChannels_noIdGiven_noErrorRaised(
        self, mock_get_questionnaire_source_choices: Mock
    ):
        mock_get_questionnaire_source_choices.return_value = {
            "id_1": "Source 1",
            "id_2": "Source 2",
        }
        cache = Mock()

        BestellWizardOrderValidator.validate_distribution_channels(
            given_channel_ids=[], cache=cache
        )

        mock_get_questionnaire_source_choices.assert_called_once_with(cache=cache)

    @patch.object(
        QuestionnaireSourceService, "get_questionnaire_source_choices", autospec=True
    )
    def test_validateDistributionChannels_allIdsValid_noErrorRaised(
        self, mock_get_questionnaire_source_choices: Mock
    ):
        mock_get_questionnaire_source_choices.return_value = {
            "id_1": "Source 1",
            "id_2": "Source 2",
            "id_3": "Source 3",
        }
        cache = Mock()

        BestellWizardOrderValidator.validate_distribution_channels(
            given_channel_ids=["id_1", "id_3"], cache=cache
        )

        mock_get_questionnaire_source_choices.assert_called_once_with(cache=cache)

    @patch.object(
        QuestionnaireSourceService, "get_questionnaire_source_choices", autospec=True
    )
    def test_validateDistributionChannels_oneIdInvalid_raisesValidationError(
        self, mock_get_questionnaire_source_choices: Mock
    ):
        mock_get_questionnaire_source_choices.return_value = {
            "id_1": "Source 1",
            "id_2": "Source 2",
            "id_3": "Source 3",
        }
        cache = Mock()

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_distribution_channels(
                given_channel_ids=["id_1", "id_4"], cache=cache
            )

        self.assertEqual("Ungültige Vertriebskanäle", error.exception.message)
        mock_get_questionnaire_source_choices.assert_called_once_with(cache=cache)
