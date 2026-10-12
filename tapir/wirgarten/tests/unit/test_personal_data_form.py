from tapir.wirgarten.forms.member import PersonalDataForm
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPersonalDataForm(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_personalDataForm_phoneNumberNotRequiredByConfig_phoneNumberFieldIsOptional(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, False)

        form = PersonalDataForm()

        self.assertFalse(form.fields["phone_number"].required)
        self.assertEqual("Telefon-Nr (optional)", form.fields["phone_number"].label)

    def test_personalDataForm_phoneNumberRequiredByConfig_phoneNumberFieldIsRequired(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, True)

        form = PersonalDataForm()

        self.assertTrue(form.fields["phone_number"].required)
        self.assertEqual("Telefon-Nr", form.fields["phone_number"].label)
