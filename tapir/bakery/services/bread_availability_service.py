from collections import Counter

from django.db.models import Case, F, IntegerField, Value, When

from tapir.bakery.models import BreadCapacityPickupLocation, BreadDelivery
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)


class BreadAvailabilityService:
    """
    Whether a bread may be put on a delivery slot.

    A bread is chosen against the capacity its station has for that week, so
    the answer depends on the station the member resolves to - which is why
    this takes the delivery rather than a location id.
    """

    @classmethod
    def is_bread_available_at_location(
        cls, bread_id, pickup_location_id, year: int, delivery_week: int
    ) -> bool:
        return BreadCapacityPickupLocation.objects.filter(
            year=year,
            delivery_week=delivery_week,
            pickup_location_id=pickup_location_id,
            bread_id=bread_id,
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
        )

    @classmethod
    def annotate_remaining_capacity(
        cls, breads, pickup_location_id, year: int, delivery_week: int, cache: dict
    ):
        """
        Narrow a Bread queryset to what the station still has room for that
        week, annotated with capacity, delivery_count and available_capacity.

        The station a delivery belongs to is derived, so the counts are
        gathered in Python and fed back in as a Case expression, which keeps
        available_capacity filterable in SQL. Only slots with a bread on them
        consume capacity, and a jokered slot is not delivered at all, so
        neither is counted.
        """
        delivery_counts = Counter(
            delivery.bread_id
            for delivery in BreadDeliveryContextService.get_deliveries_for_location_for_week(
                year=year,
                delivery_week=delivery_week,
                pickup_location_id=pickup_location_id,
                cache=cache,
                queryset=BreadDelivery.objects.filter(
                    bread__isnull=False,
                    subscription__product__type__is_bread=True,
                ),
            )
        )

        return (
            breads.filter(
                capacity_entries__pickup_location_id=pickup_location_id,
                capacity_entries__year=year,
                capacity_entries__delivery_week=delivery_week,
            )
            .annotate(
                capacity=F("capacity_entries__capacity"),
                delivery_count=Case(
                    *[
                        When(pk=bread_id, then=Value(count))
                        for bread_id, count in delivery_counts.items()
                    ],
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            )
            .annotate(available_capacity=F("capacity") - F("delivery_count"))
            .filter(available_capacity__gt=0)
            .distinct()
        )
