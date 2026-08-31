from django.db.models import QuerySet

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys


def filter_pickup_locations_for_growing_period(
    queryset: QuerySet, growing_period_id: str | None, cache: dict
) -> QuerySet:
    """
    If the period-assignment feature is disabled, return the queryset untouched.
    Otherwise restrict the queryset to PickupLocations that are assigned to the
    given growing_period. If growing_period_id is None and the feature is on,
    return an empty queryset (caller is asking "for no specific period" while
    the feature is enabled, which is meaningless – treat as no locations).
    """
    if not get_parameter_value(
        key=ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED, cache=cache
    ):
        return queryset
    if growing_period_id is None:
        return queryset.none()
    return queryset.filter(growing_period_links__growing_period_id=growing_period_id)
