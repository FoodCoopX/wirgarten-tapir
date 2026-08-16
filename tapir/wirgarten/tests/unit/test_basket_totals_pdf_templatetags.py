from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.templatetags.wirgarten import (
    grand_total_route_baskets,
    organisation_logo_data_uri,
    site_name_for_pdf,
    sum_across_route_basket_totals,
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

    def test_grandTotalRouteBaskets_sumsAllTotals(self):
        entries = [
            {"route_basket_totals": {"totals": {"small": 2, "normal": 3}}},
            {"route_basket_totals": {"totals": {"small": 1, "normal": None}}},
            {},
        ]

        self.assertEqual(6, grand_total_route_baskets(entries))
        self.assertEqual(0, grand_total_route_baskets(None))
        self.assertEqual(0, grand_total_route_baskets([]))

    def test_sumAcrossRouteBasketTotals_sumsOneHeader(self):
        entries = [
            {"route_basket_totals": {"totals": {"small": 2, "normal": 5}}},
            {"route_basket_totals": {"totals": {"small": None, "normal": 1}}},
            {"route_basket_totals": {}},
        ]

        self.assertEqual(2, sum_across_route_basket_totals(entries, "small"))
        self.assertEqual(6, sum_across_route_basket_totals(entries, "normal"))
        self.assertEqual(0, sum_across_route_basket_totals(None, "small"))
        self.assertEqual(0, sum_across_route_basket_totals(entries, "missing"))
