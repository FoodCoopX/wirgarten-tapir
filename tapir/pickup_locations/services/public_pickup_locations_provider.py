from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_growing_period_filter import (
    filter_pickup_locations_for_growing_period,
)
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys


class PublicPickupLocationProvider:
    @classmethod
    def get_pickup_locations_available_for_members(
        cls, cache: dict, growing_period_id: str | None = None
    ):
        qs = PickupLocation.objects.order_by("name").exclude(
            id=get_parameter_value(
                key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                cache=cache,
            )
        )

        # When the period-assignment feature is on and no growing_period_id is
        # supplied (e.g. legacy callers like the bestellwizard base data
        # endpoint), fall back to the GrowingPeriod covering today's contract
        # start date. Otherwise the member sees no pickup locations at all.
        if growing_period_id is None and get_parameter_value(
            key=ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED, cache=cache
        ):
            from tapir.subscriptions.services.contract_start_date_calculator import (
                ContractStartDateCalculator,
            )
            from tapir.wirgarten.models import GrowingPeriod
            from tapir.wirgarten.utils import get_today

            subscription_start = (
                ContractStartDateCalculator.get_next_contract_start_date(
                    reference_date=get_today(cache=cache),
                    apply_buffer_time=True,
                    cache=cache,
                )
            )
            gp = GrowingPeriod.objects.filter(
                start_date__lte=subscription_start, end_date__gte=subscription_start
            ).first()
            if gp is not None:
                growing_period_id = gp.id

        return filter_pickup_locations_for_growing_period(qs, growing_period_id, cache)
