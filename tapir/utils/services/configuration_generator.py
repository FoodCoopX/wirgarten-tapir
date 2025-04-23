from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.utils.config import Organization
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys


class ConfigurationGenerator:
    @classmethod
    def update_settings_for_organization(cls, organization):
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value=organization == Organization.BIOTOP
        )

        picking_modes = {
            Organization.BIOTOP: PICKING_MODE_BASKET,
            Organization.WIRGARTEN: PICKING_MODE_SHARE,
        }
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=picking_modes[organization]
        )

        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=organization == Organization.BIOTOP)

        delivery_day = {
            Organization.BIOTOP: 4,
            Organization.WIRGARTEN: 2,
        }
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(
            value=delivery_day[organization]
        )

        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=ProductType.objects.get(name="Ernteanteile").id
        )
