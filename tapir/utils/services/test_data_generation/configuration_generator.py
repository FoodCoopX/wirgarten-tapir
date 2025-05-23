from tapir.configuration.models import TapirParameter
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COMPANY,
)
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.utils.config import Organization
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys


class ConfigurationGenerator:
    @classmethod
    def update_settings_for_organization(cls, organization):
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value=organization in [Organization.BIOTOP, Organization.VEREIN]
        )

        legal_statuses = {
            Organization.BIOTOP: LEGAL_STATUS_COOPERATIVE,
            Organization.WIRGARTEN: LEGAL_STATUS_COOPERATIVE,
            Organization.VEREIN: LEGAL_STATUS_ASSOCIATION,
            Organization.L2G: LEGAL_STATUS_COMPANY,
        }
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=legal_statuses[organization])

        picking_modes = {
            Organization.BIOTOP: PICKING_MODE_BASKET,
            Organization.WIRGARTEN: PICKING_MODE_SHARE,
            Organization.VEREIN: PICKING_MODE_SHARE,
            Organization.L2G: PICKING_MODE_SHARE,
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
            Organization.VEREIN: 2,
            Organization.L2G: 3,
        }
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(
            value=delivery_day[organization]
        )

        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=ProductType.objects.get(name="Ernteanteile").id
        )

        if organization == Organization.BIOTOP:
            TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DUE_DAY).update(
                value=5
            )
            TapirParameter.objects.filter(
                key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
            ).update(value=True)
            TapirParameter.objects.filter(
                key=ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
            ).update(value=True)
