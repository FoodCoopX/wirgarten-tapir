from collections.abc import Collection

from django.db.models import Case, IntegerField, Value, When

from tapir.bakery.models import AvailableBreadsForDeliveryDay
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.services.direct_order_limit_service import (
    DirectOrderLimitService,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)


class BreadAvailabilityService:
    """
    Whether a bread may be put on a delivery slot: a station offers every
    bread baked on its delivery day that week.
    """

    @classmethod
    def is_bread_available_at_location(
        cls, bread_id, pickup_location_id, year: int, delivery_week: int, cache: dict
    ) -> bool:
        delivery_day = PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id, cache=cache
        )
        if delivery_day is None:
            return False
        return AvailableBreadsForDeliveryDay.objects.filter(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            bread_id=bread_id,
            bread__is_active=True,
        ).exists()

    @classmethod
    def is_bread_available_for_delivery(cls, delivery, bread, cache: dict) -> bool:
        """
        A member with no station for that week has nothing to check against, so
        the choice is allowed rather than blocked by missing setup.
        """
        if bread is None:
            return True

        pickup_location_id = BreadDeliveryContextService.get_pickup_location_id(
            delivery, cache=cache
        )
        if not pickup_location_id:
            return True

        return cls.is_bread_available_at_location(
            bread_id=bread.pk,
            pickup_location_id=pickup_location_id,
            year=delivery.year,
            delivery_week=delivery.delivery_week,
            cache=cache,
        )

    @classmethod
    def annotate_remaining_capacity(
        cls,
        breads,
        pickup_location_id,
        year: int,
        delivery_week: int,
        cache: dict,
        exclude_delivery_ids: Collection[str] = (),
    ):
        """
        Narrow a Bread queryset to what members of the station can still choose
        that week, annotated with capacity (the direct-order limit),
        delivery_count (the direct orders on that delivery day, all stations)
        and available_capacity (what is left of the bread's limit and its
        group's). capacity is None when the bread has no limit of its own,
        available_capacity when neither it nor its group has one.

        exclude_delivery_ids leaves the slot being chosen for out of the
        counts, as BreadChoiceService.check_capacity_available does.
        """
        delivery_day = PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id, cache=cache
        )
        if delivery_day is None:
            return breads.none()

        limits = DirectOrderLimitService.get_limits_for_day(
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
            cache=cache,
            exclude_delivery_ids=exclude_delivery_ids,
        )
        remaining = {bread_id: limits.remaining(bread_id) for bread_id in limits.breads}
        open_bread_ids = [
            bread_id for bread_id, left in remaining.items() if left is None or left > 0
        ]

        def per_bread(values: dict):
            return Case(
                *[
                    When(pk=bread_id, then=Value(value))
                    for bread_id, value in values.items()
                ],
                default=Value(None),
                output_field=IntegerField(),
            )

        return breads.filter(pk__in=open_bread_ids).annotate(
            capacity=per_bread(
                {bread_id: limit.limit for bread_id, limit in limits.breads.items()}
            ),
            delivery_count=per_bread(
                {bread_id: limit.ordered for bread_id, limit in limits.breads.items()}
            ),
            available_capacity=per_bread(remaining),
        )
