from tapir.bestell_wizard.views import BestellWizardBaseDataApiView
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildSimpleResponseFields(TapirUnitTest):
    def test_buildSimpleResponseFields_default_returnsCorrectDictionary(self):
        cache = {}

        mock_parameter_value(
            key=ParameterKeys.COOP_SHARE_PRICE,
            value="test_coop_share_price",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.ORGANISATION_THEME,
            value="test_organisation_theme",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
            value="test_coop_shares_independent",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_FORCE_WAITING_LIST,
            value="test_force_waiting_list",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_SHOW_INTRO,
            value="test_show_intro",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
            value="test_allow_student",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_INTRO_TEXT,
            value="test_intro_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_SEPA_MANDAT_CHECKBOX_TEXT,
            value="test_sepa_mandat",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
            value="test_contract_policy",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM,
            value="test_default_rhythm",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.COOP_STATUTE_LINK, value="test_statute_link", cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.SITE_NAME, value="test_site_name", cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.SITE_EMAIL, value="test_site_email", cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.SOLIDARITY_DEFAULT,
            value="test_solidarity_default",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP13_ENABLED,
            value="test_step13",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELL_WIZARD_SOLIDARITY_STEP_POSITION,
            value="test_step_position",
            cache=cache,
        )

        result = BestellWizardBaseDataApiView.build_simple_response_fields(cache=cache)

        self.assertEqual(
            {
                "price_of_a_share": "test_coop_share_price",
                "theme": "test_organisation_theme",
                "allow_investing_membership": "test_coop_shares_independent",
                "force_waiting_list": "test_force_waiting_list",
                "intro_enabled": "test_show_intro",
                "student_status_allowed": "test_allow_student",
                "intro_step_text": "test_intro_text",
                "label_checkbox_sepa_mandat": "test_sepa_mandat",
                "label_checkbox_contract_policy": "test_contract_policy",
                "default_payment_rhythm": "test_default_rhythm",
                "coop_statute_link": "test_statute_link",
                "organization_name": "test_site_name",
                "contact_mail_address": "test_site_email",
                "solidarity_contribution_default": "test_solidarity_default",
                "feedback_step_enabled": "test_step13",
                "solidarity_step_position": "test_step_position",
            },
            result,
        )
