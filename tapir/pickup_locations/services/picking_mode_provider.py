from tapir.configuration.parameter import get_parameter_value
from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.wirgarten.parameter_keys import ParameterKeys


class PickingModeProvider:
    @staticmethod
    def get_picking_mode(
        cache: dict,
    ):
        picking_mode = get_parameter_value(key=ParameterKeys.PICKING_MODE, cache=cache)
        valid_modes = [PICKING_MODE_BASKET, PICKING_MODE_SHARE]
        if picking_mode not in valid_modes:
            raise TapirImproperlyConfigured(
                f"Unknown picking mode: {picking_mode}, valid modes are: {valid_modes}"
            )
        return picking_mode
