from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.utils.config import Organization
from tapir.wirgarten.parameters import Parameter


class TestConfigurationGenerator:
    @classmethod
    def update_settings_for_organization(cls, organization):
        TapirParameter.objects.filter(key=Parameter.JOKERS_ENABLED).update(
            value=organization == Organization.BIOTOP
        )

        picking_modes = {
            Organization.BIOTOP: PICKING_MODE_BASKET,
            Organization.WIRGARTEN: PICKING_MODE_SHARE,
        }
        TapirParameter.objects.filter(key=Parameter.PICKING_MODE).update(
            value=picking_modes[organization]
        )

        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=organization == Organization.BIOTOP)

        delivery_day = {
            Organization.BIOTOP: 4,
            Organization.WIRGARTEN: 2,
        }
        TapirParameter.objects.filter(key=Parameter.DELIVERY_DAY).update(
            value=delivery_day[organization]
        )
