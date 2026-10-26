from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

PUBLIC_TEXT_KEYS = [
    ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
    ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
    ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
    ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
    ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TEXT,
    ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TITLE,
    ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TEXT,
    ParameterKeys.BIDDING_ROUND_PUBLIC_SUMMARY_TITLE,
    ParameterKeys.BIDDING_ROUND_PUBLIC_SUBMIT_LABEL,
    ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TITLE,
    ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TEXT,
    ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_EXPLANATION,
    ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TRAFFIC_LIGHT_SLIDER_HINT,
    ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_SIMPLE_LEVELS_SLIDER_HINT,
    ParameterKeys.BIDDING_ROUND_BID_PRODUCT_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_VARIANT_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_QUANTITY_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_AMOUNT_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_REFERENCE_VALUE_HINT,
    ParameterKeys.BIDDING_ROUND_BID_SIMPLE_EXPLANATION,
    ParameterKeys.BIDDING_ROUND_BID_TRAFFIC_LIGHT_EXPLANATION,
    ParameterKeys.BIDDING_ROUND_BID_SIMPLE_LEVELS_EXPLANATION,
    ParameterKeys.BIDDING_ROUND_BID_LEVEL_1_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_LEVEL_2_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_LEVEL_3_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_GREEN_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_YELLOW_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_RED_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_PICKUP_LOCATION_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_LIVE_YEARLY_LABEL,
    ParameterKeys.BIDDING_ROUND_BID_MONTHLY_HINT,
    ParameterKeys.BIDDING_ROUND_BID_MONTHLY_UNIT,
    ParameterKeys.BIDDING_ROUND_BID_CONFIRM_TEXT,
    ParameterKeys.BIDDING_ROUND_BID_SUCCESS_TEXT,
    ParameterKeys.BIDDING_ROUND_BID_ERROR_TEXT,
]


class TestParameterDefinitions(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_parametersImported_defaultsMatch(self):
        self.assertFalse(
            TapirParameter.objects.get(
                key=ParameterKeys.BIDDING_ROUND_ENABLED
            ).get_value()
        )
        self.assertTrue(
            TapirParameter.objects.get(
                key=ParameterKeys.BIDDING_ROUND_URL_ENABLED
            ).get_value()
        )
        self.assertFalse(
            TapirParameter.objects.get(
                key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
            ).get_value()
        )
        self.assertTrue(
            TapirParameter.objects.get(
                key=ParameterKeys.BIDDING_ROUND_STATS_INCLUDE_AUTO_RENEWED
            ).get_value()
        )

    def test_publicTexts_defaultsNonEmpty(self):
        for key in PUBLIC_TEXT_KEYS:
            with self.subTest(key=key):
                self.assertTrue(TapirParameter.objects.get(key=key).get_value())

    def test_publicEndedText_containsBestellWizardLink(self):
        ended_text = TapirParameter.objects.get(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT
        ).get_value()
        self.assertIn("/bestell_wizard/bestell_wizard_mobile", ended_text)
