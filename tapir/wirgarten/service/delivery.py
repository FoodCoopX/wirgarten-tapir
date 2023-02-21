from datetime import date

from dateutil.relativedelta import relativedelta

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import PickupLocationCapability, PickupLocation
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_active_product_types


def get_active_pickup_location_capabilities():
    return PickupLocationCapability.objects.filter(
        product_type__in=get_active_product_types()
    )


def get_active_pickup_locations(
    capabilities: [
        PickupLocationCapability
    ] = get_active_pickup_location_capabilities(),
):
    return PickupLocation.objects.filter(
        id__in=capabilities.values("pickup_location__id")
    )


def get_next_delivery_date(reference_date: date = date.today()):
    delivery_day = get_parameter_value(Parameter.DELIVERY_DAY)
    if reference_date.weekday() > delivery_day:
        next_delivery = reference_date + relativedelta(
            days=(7 - reference_date.weekday() % 7) + delivery_day
        )
    else:
        next_delivery = reference_date + relativedelta(
            days=delivery_day - reference_date.weekday()
        )
    return next_delivery
