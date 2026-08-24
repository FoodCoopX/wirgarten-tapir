from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.templatetags.wirgarten import (
    organisation_logo_data_uri,
    site_name_for_pdf,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBasketTotalsPdfTemplatetags(TapirUnitTest):
    @patch("tapir.wirgarten.templatetags.wirgarten.get_parameter_value")
    def test_organisationLogoDataUri_noTheme_returnsEmpty(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = ""

        self.assertEqual("", organisation_logo_data_uri())
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.ORGANISATION_THEME, cache={}
        )

    @patch("tapir.wirgarten.templatetags.wirgarten.find")
    @patch("tapir.wirgarten.templatetags.wirgarten.get_parameter_value")
    def test_organisationLogoDataUri_themeWithoutLogoFile_returnsEmpty(
        self, mock_get_parameter_value: Mock, mock_find: Mock
    ):
        mock_get_parameter_value.return_value = "biotop"
        mock_find.return_value = None

        self.assertEqual("", organisation_logo_data_uri())
        mock_find.assert_called_once_with("core/themes/biotop/images/Logo_white.webp")

    @patch("tapir.wirgarten.templatetags.wirgarten.find")
    @patch("tapir.wirgarten.templatetags.wirgarten.get_parameter_value")
    def test_organisationLogoDataUri_logoFound_returnsDataUri(
        self, mock_get_parameter_value: Mock, mock_find: Mock
    ):
        mock_get_parameter_value.return_value = "biotop"
        with NamedTemporaryFile(suffix=".webp") as tmp:
            tmp.write(b"fake-webp-bytes")
            tmp.flush()
            mock_find.return_value = tmp.name

            result = organisation_logo_data_uri()

        self.assertTrue(result.startswith("data:image/webp;base64,"))
        self.assertIn("ZmFrZS13ZWJwLWJ5dGVz", result)

    @patch("tapir.wirgarten.templatetags.wirgarten.get_parameter_value")
    def test_siteNameForPdf_returnsParameterValue(self, mock_get_parameter_value: Mock):
        mock_get_parameter_value.return_value = "Gärtnerei Test"

        self.assertEqual("Gärtnerei Test", site_name_for_pdf())
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SITE_NAME, cache={}
        )
