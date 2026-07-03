from tapir.bestell_wizard.views import BestellWizardBaseDataApiView
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildStringsObject(TapirUnitTest):
    def test_buildStringsObject_default_returnsCorrectDictionary(self):
        cache = {}

        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP1A_TITLE,
            value="test_step1a_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP1A_TEXT,
            value="test_step1a_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP1B_TITLE,
            value="test_step1b_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP1B_TEXT,
            value="test_step1b_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP2_TITLE,
            value="test_step2_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP2_TEXT,
            value="test_step2_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP3_TITLE,
            value="test_step3_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP3_TEXT,
            value="test_step3_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP3_NAME_SUPPORTING_MEMBERSHIP,
            value="test_step3_supporting_membership_name",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP3B_TITLE,
            value="test_step3b_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP3B_TEXT,
            value="test_step3b_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_HEADER,
            value="test_step4b_waiting_list_modal_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_TEXT,
            value="test_step4b_waiting_list_modal_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_TITLE,
            value="test_step4d_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_TEXT,
            value="test_step4d_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_TEXT_SUPPORTING_MEMBER,
            value="test_step4d_text_supporting_member",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP5A_TITLE,
            value="test_step5a_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP5A_TEXT,
            value="test_step5a_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP5B_TITLE,
            value="test_step5b_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP5C_TITLE,
            value="test_step5c_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP5C_TEXT,
            value="test_step5c_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6A_TITLE,
            value="test_step6a_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6A_TEXT,
            value="test_step6a_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6B_TITLE,
            value="test_step6b_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6B_TEXT,
            value="test_step6b_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6B_CHECKBOX_STATUTE_ASSOCIATIONS,
            value="test_step6b_checkbox_statute_associations",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_TITLE,
            value="test_step6c_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_TEXT,
            value="test_step6c_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_STATUTE,
            value="test_step6c_checkbox_statute",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_TEXT_STATUTE,
            value="test_step6c_text_statute",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_COMMITMENT,
            value="test_step6c_checkbox_commitment",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP8_TITLE,
            value="test_step8_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP8_TEXT,
            value="test_step8_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP9_TITLE,
            value="test_step9_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP9_PAYMENT_RHYTHM_MODAL_TEXT,
            value="test_step9_payment_rhythm_modal_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP10_TITLE,
            value="test_step10_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP10_SINGLE_PRODUCT_TYPE_HINT,
            value="test_step_10_single_product_type_hint",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP11_TITLE,
            value="test_step11_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_PRIVACY_POLICY_LABEL,
            value="test_step11_privacy_policy_label",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_PRIVACY_POLICY_EXPLANATION,
            value="test_step11_privacy_policy_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_LABEL,
            value="test_step11_revocation_label",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_EXPLANATION,
            value="test_step11_revocation_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP12_TITLE,
            value="test_step12_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP13_TITLE,
            value="test_step13_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP13_TEXT,
            value="test_step13_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP14_TITLE,
            value="test_step14_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP14_TEXT,
            value="test_step14_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP14B_TITLE,
            value="test_step14b_title",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP14B_TEXT,
            value="test_step14b_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.SITE_PRIVACY_LINK,
            value="test_privacy_policy_url",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.LABEL_STUDENT_CHECKBOX,
            value="test_label_student_checkbox",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.STUDENT_CHECKBOX_EXPLANATION_TEXT,
            value="test_student_checkbox_explanation_text",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP10_FLAG_STUDENT,
            value="test_step10_flag_student",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP10_TEXT_STUDENT,
            value="test_step10_text_student",
            cache=cache,
        )

        result = BestellWizardBaseDataApiView.build_strings_object(cache=cache)

        self.assertEqual(
            {
                "step1a_title": "test_step1a_title",
                "step1a_text": "test_step1a_text",
                "step1b_title": "test_step1b_title",
                "step1b_text": "test_step1b_text",
                "step2_title": "test_step2_title",
                "step2_text": "test_step2_text",
                "step3_title": "test_step3_title",
                "step3_text": "test_step3_text",
                "step3_supporting_membership_name": "test_step3_supporting_membership_name",
                "step3b_title": "test_step3b_title",
                "step3b_text": "test_step3b_text",
                "step4b_waiting_list_modal_title": "test_step4b_waiting_list_modal_title",
                "step4b_waiting_list_modal_text": "test_step4b_waiting_list_modal_text",
                "step4d_title": "test_step4d_title",
                "step4d_text": "test_step4d_text",
                "step4d_text_supporting_member": "test_step4d_text_supporting_member",
                "step5a_title": "test_step5a_title",
                "step5a_text": "test_step5a_text",
                "step5b_title": "test_step5b_title",
                "step5c_title": "test_step5c_title",
                "step5c_text": "test_step5c_text",
                "step6a_title": "test_step6a_title",
                "step6a_text": "test_step6a_text",
                "step6b_title": "test_step6b_title",
                "step6b_text": "test_step6b_text",
                "step6b_checkbox_statute_associations": "test_step6b_checkbox_statute_associations",
                "step6c_title": "test_step6c_title",
                "step6c_text": "test_step6c_text",
                "step6c_checkbox_statute": "test_step6c_checkbox_statute",
                "step6c_text_statute": "test_step6c_text_statute",
                "step6c_checkbox_commitment": "test_step6c_checkbox_commitment",
                "step8_title": "test_step8_title",
                "step8_text": "test_step8_text",
                "step9_title": "test_step9_title",
                "step9_payment_rhythm_modal_text": "test_step9_payment_rhythm_modal_text",
                "step10_title": "test_step10_title",
                "step_10_single_product_type_hint": "test_step_10_single_product_type_hint",
                "step11_title": "test_step11_title",
                "step11_privacy_policy_label": "test_step11_privacy_policy_label",
                "step11_privacy_policy_text": "test_step11_privacy_policy_text",
                "step11_revocation_label": "test_step11_revocation_label",
                "step11_revocation_text": "test_step11_revocation_text",
                "step12_title": "test_step12_title",
                "step13_title": "test_step13_title",
                "step13_text": "test_step13_text",
                "step14_title": "test_step14_title",
                "step14_text": "test_step14_text",
                "step14b_title": "test_step14b_title",
                "step14b_text": "test_step14b_text",
                "privacy_policy_url": "test_privacy_policy_url",
                "label_student_checkbox": "test_label_student_checkbox",
                "student_checkbox_explanation_text": "test_student_checkbox_explanation_text",
                "step10_flag_student": "test_step10_flag_student",
                "step10_text_student": "test_step10_text_student",
            },
            result,
        )
