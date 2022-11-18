from tapir.wirgarten.models import PickupLocationCapability, PickupLocation
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
