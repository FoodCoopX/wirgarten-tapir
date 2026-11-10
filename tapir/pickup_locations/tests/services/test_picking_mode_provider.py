from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.pickup_locations.config import PICKING_MODE_BASKET
from tapir.pickup_locations.services.picking_mode_provider import PickingModeProvider
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestPickingModeProvider(TapirUnitTest):
    def test_getPickingMode_modeIsValid_returnsMode(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.PICKING_MODE, value=PICKING_MODE_BASKET
        )

        result = PickingModeProvider.get_picking_mode(cache=cache)

        self.assertEqual(PICKING_MODE_BASKET, result)

    def test_getPickingMode_modeIsInvalid_raisesError(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.PICKING_MODE, value="invalid"
        )

        with self.assertRaisesMessage(
            TapirImproperlyConfigured,
            "Unknown picking mode: invalid, valid modes are: ['picking_mode_basket', 'picking_mode_share']",
        ):
            PickingModeProvider.get_picking_mode(cache=cache)
