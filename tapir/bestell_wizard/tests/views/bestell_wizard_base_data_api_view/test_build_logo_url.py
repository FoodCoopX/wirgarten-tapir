from unittest.mock import patch

from tapir.bestell_wizard.views import BestellWizardBaseDataApiView
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildLogoUrl(TapirUnitTest):
    def setUp(self):
        self.cache = {}
        mock_parameter_value(
            key=ParameterKeys.ORGANISATION_THEME, value="akv", cache=self.cache
        )

    @patch("tapir.bestell_wizard.views.static", side_effect=lambda path: "/" + path)
    @patch("tapir.bestell_wizard.views.staticfiles_storage")
    def test_buildLogoUrl_themeHasDarkLogo_returnsDarkLogo(self, storage, _):
        storage.exists.return_value = True

        self.assertEqual(
            "/core/themes/akv/images/Logo_dark.webp",
            BestellWizardBaseDataApiView.build_logo_url(cache=self.cache),
        )
        storage.exists.assert_called_once_with("core/themes/akv/images/Logo_dark.webp")

    @patch("tapir.bestell_wizard.views.static", side_effect=lambda path: "/" + path)
    @patch("tapir.bestell_wizard.views.staticfiles_storage")
    def test_buildLogoUrl_themeWithoutDarkLogo_returnsWhiteLogo(self, storage, _):
        storage.exists.return_value = False

        self.assertEqual(
            "/core/themes/akv/images/Logo_white.webp",
            BestellWizardBaseDataApiView.build_logo_url(cache=self.cache),
        )
