from django.test import override_settings

from tapir.configuration.forms import ParameterForm
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestParameterForm(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @override_settings(BAKERY_ENABLED=False)
    def test_init_bakeryDisabled_bakeryCategoryIsHidden(self):
        form = ParameterForm()

        self.assertNotIn(ParameterCategory.BAKERY, form.categories)
        self.assertNotIn(ParameterKeys.BAKERY_STOVE_LAYERS, form.fields)

    @override_settings(BAKERY_ENABLED=True)
    def test_init_bakeryEnabled_bakeryCategoryIsShown(self):
        form = ParameterForm()

        self.assertIn(ParameterCategory.BAKERY, form.categories)
        self.assertIn(ParameterKeys.BAKERY_STOVE_LAYERS, form.fields)

    def test_isValid_stringValueLongerThanDatabaseColumn_fieldHasError(self):
        form = ParameterForm(data={ParameterKeys.SITE_NAME: "a" * 4097})

        self.assertFalse(form.is_valid())
        self.assertIn(ParameterKeys.SITE_NAME, form.errors)

    def test_init_depositIncrement_isOnlyShownWhenHigherDepositsAreAllowed(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        self.assertNotIn(
            ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, ParameterForm().fields
        )

        for key in (
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP,
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE,
        ):
            with self.subTest(key=key):
                self._set_parameter(key, True)
                self.assertIn(
                    ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, ParameterForm().fields
                )
                self._set_parameter(key, False)
