from unittest.mock import patch, Mock, call

from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tasks import export_pick_list_csv
from tapir.wirgarten.tests.factories import ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestExportPickListCls(TapirUnitTest):
    @patch("tapir.wirgarten.tasks.should_export_list_today", autospec=True)
    @patch("tapir.wirgarten.tasks._export_pick_list", autospec=True)
    @patch("tapir.wirgarten.tasks.get_active_product_types", autospec=True)
    def test_exportPickListCsv_shouldNotExportToday_dontExport(
        self,
        mock_get_active_product_types: Mock,
        mock_export_pick_list: Mock,
        mock_should_export_list_today: Mock,
    ):
        cache = Mock()
        mock_should_export_list_today.return_value = False

        export_pick_list_csv(cache)

        mock_get_active_product_types.assert_not_called()
        mock_export_pick_list.assert_not_called()
        mock_should_export_list_today.assert_called_once_with(cache=cache)

    @patch("tapir.wirgarten.tasks.should_export_list_today", autospec=True)
    @patch("tapir.wirgarten.tasks._export_pick_list", autospec=True)
    @patch("tapir.wirgarten.tasks.get_active_product_types", autospec=True)
    def test_exportPickListCsv_noActiveProducts_dontExport(
        self,
        mock_get_active_product_types: Mock,
        mock_export_pick_list: Mock,
        mock_should_export_list_today: Mock,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PICKING_PRODUCT_TYPES,
            value="Ernteanteile;Hühneranteile",
        )
        mock_get_active_product_types.return_value = []
        mock_should_export_list_today.return_value = True

        export_pick_list_csv(cache)

        mock_get_active_product_types.assert_called_once_with(cache=cache)
        mock_export_pick_list.assert_not_called()
        mock_should_export_list_today.assert_called_once_with(cache=cache)

    @patch("tapir.wirgarten.tasks.should_export_list_today", autospec=True)
    @patch("tapir.wirgarten.tasks._export_pick_list", autospec=True)
    @patch("tapir.wirgarten.tasks.get_active_product_types", autospec=True)
    def test_exportPickListCsv_parameterValueIsAlle_exportAllProducts(
        self,
        mock_get_active_product_types: Mock,
        mock_export_pick_list: Mock,
        mock_should_export_list_today: Mock,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PICKING_PRODUCT_TYPES,
            value="alle",
        )
        product_types = ProductTypeFactory.build_batch(size=3)
        mock_get_active_product_types.return_value = product_types
        mock_should_export_list_today.return_value = True

        export_pick_list_csv(cache)

        mock_get_active_product_types.assert_called_once_with(cache=cache)
        mock_should_export_list_today.assert_called_once_with(cache=cache)
        self.assertEqual(3, mock_export_pick_list.call_count)
        mock_export_pick_list.assert_has_calls(
            [call(product_type, True, cache=cache) for product_type in product_types],
            any_order=True,
        )

    @patch("tapir.wirgarten.tasks.should_export_list_today", autospec=True)
    @patch("tapir.wirgarten.tasks._export_pick_list", autospec=True)
    @patch("tapir.wirgarten.tasks.get_active_product_types", autospec=True)
    def test_exportPickListCsv_someProductsSelected_exportOnlySelectedProducts(
        self,
        mock_get_active_product_types: Mock,
        mock_export_pick_list: Mock,
        mock_should_export_list_today: Mock,
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PICKING_PRODUCT_TYPES,
            value="Hühneranteile,Ernteanteile",
        )
        product_types = ProductTypeFactory.build_batch(size=3)
        product_types[0].name = "Ernteanteile"
        product_types[2].name = "Hühneranteile"
        mock_get_active_product_types.return_value = product_types
        mock_should_export_list_today.return_value = True

        export_pick_list_csv(cache)

        mock_get_active_product_types.assert_called_once_with(cache=cache)
        mock_should_export_list_today.assert_called_once_with(cache=cache)
        self.assertEqual(2, mock_export_pick_list.call_count)
        mock_export_pick_list.assert_has_calls(
            [
                call(product_type, True, cache=cache)
                for product_type in [product_types[0], product_types[2]]
            ],
            any_order=True,
        )
