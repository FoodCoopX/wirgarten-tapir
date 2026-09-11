from tapir.bestell_wizard.views import BestellWizardBaseDataApiView
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildImagesObject(TapirUnitTest):
    def test_buildImagesObject_default_returnsCorrectDictionary(self):
        cache = {}

        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP1_BACKGROUND_IMAGE,
            value="test_step1_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP2_BACKGROUND_IMAGE,
            value="test_step2_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP3_BACKGROUND_IMAGE,
            value="test_step3_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_BACKGROUND_IMAGE,
            value="test_step4d_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP5_BACKGROUND_IMAGE,
            value="test_step5_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP6_BACKGROUND_IMAGE,
            value="test_step6_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP8_BACKGROUND_IMAGE,
            value="test_step8_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP9_BACKGROUND_IMAGE,
            value="test_step9_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP10_BACKGROUND_IMAGE,
            value="test_step10_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP11_BACKGROUND_IMAGE,
            value="test_step11_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP12_BACKGROUND_IMAGE,
            value="test_step12_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP13_BACKGROUND_IMAGE,
            value="test_step13_background_image",
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_STEP14_BACKGROUND_IMAGE,
            value="test_step14_background_image",
            cache=cache,
        )

        result = BestellWizardBaseDataApiView.build_images_object(cache=cache)

        self.assertEqual(
            {
                "step1_background_image": "test_step1_background_image",
                "step2_background_image": "test_step2_background_image",
                "step3_background_image": "test_step3_background_image",
                "step4d_background_image": "test_step4d_background_image",
                "step5_background_image": "test_step5_background_image",
                "step6_background_image": "test_step6_background_image",
                "step8_background_image": "test_step8_background_image",
                "step9_background_image": "test_step9_background_image",
                "step10_background_image": "test_step10_background_image",
                "step11_background_image": "test_step11_background_image",
                "step12_background_image": "test_step12_background_image",
                "step13_background_image": "test_step13_background_image",
                "step14_background_image": "test_step14_background_image",
            },
            result,
        )
