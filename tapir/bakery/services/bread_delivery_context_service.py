import datetime
import logging
from collections import Counter
from collections.abc import Collection

from tapir.bakery.models import BreadDelivery
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_from_cache_or_compute, week_to_monday
from tapir.wirgarten.service.delivery import get_next_delivery_date

logger = logging.getLogger(__name__)


class BreadDeliveryContextService:
    """
    Derives a bread delivery's pickup location and joker status.

    The codebase has four non-equivalent ways to resolve a member's pickup
    location, and picking a different one changes who appears on the Abholliste.
    """

    @classmethod
    def get_reference_date(
        cls, year: int, delivery_week: int, cache: dict
    ) -> datetime.date:
        """
        The date on which a delivery in this ISO week actually happens.

        Mirrors GetDeliveriesService.build_delivery_object.
        """
        reference_dates = get_from_cache_or_compute(
            cache, "bread_delivery_reference_dates", lambda: {}
        )
        return get_from_cache_or_compute(
            reference_dates,
            (year, delivery_week),
            lambda: get_next_delivery_date(
                week_to_monday(year, delivery_week), cache=cache
            ),
        )

    @classmethod
    def get_pickup_location_id(cls, delivery: BreadDelivery, cache: dict) -> str | None:
        """Requires the delivery to carry its subscription (select_related)."""
        return cls._get_member_pickup_location_id(
            delivery.subscription.member_id,
            delivery.year,
            delivery.delivery_week,
            cache=cache,
        )

    @classmethod
    def _get_member_pickup_location_id(
        cls, member_id, year: int, delivery_week: int, cache: dict
    ) -> str | None:
        return MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
            member_id=member_id,
            reference_date=cls.get_reference_date(year, delivery_week, cache=cache),
            cache=cache,
        )

    @classmethod
    def get_pickup_location(cls, delivery: BreadDelivery, cache: dict):
        pickup_location_id = cls.get_pickup_location_id(delivery, cache=cache)
        if pickup_location_id is None:
            return None
        return TapirCache.get_pickup_location_by_id(
            cache=cache, pickup_location_id=pickup_location_id
        )

    @classmethod
    def is_joker_taken(cls, delivery: BreadDelivery, cache: dict) -> bool:
        """Requires the delivery to carry its subscription (select_related)."""
        return cls._has_member_taken_joker(
            delivery.subscription.member_id,
            delivery.year,
            delivery.delivery_week,
            cache=cache,
        )

    @classmethod
    def _has_member_taken_joker(
        cls, member_id, year: int, delivery_week: int, cache: dict
    ) -> bool:
        return JokerManagementService.does_member_have_a_joker_in_week(
            member_id=member_id,
            reference_date=cls.get_reference_date(year, delivery_week, cache=cache),
            cache=cache,
        )

    @classmethod
    def count_chosen_breads_for_delivery_day(
        cls,
        year: int,
        delivery_week: int,
        delivery_day: int,
        cache: dict,
        bread_ids: Collection[str],
        exclude_delivery_ids: Collection[str] = (),
    ) -> Counter:
        """
        How many slots members chose each of the breads for, over all
        stations delivered that day; jokered slots left out. The same
        deliveries get_deliveries_by_location_for_week finds, read as
        (bread, member) pairs only: a member's choice is checked against these
        counts while it holds row locks (see warm_caches_for_week).
        """
        choices = list(
            BreadDelivery.objects.filter(
                year=year, delivery_week=delivery_week, bread_id__in=bread_ids
            )
            .exclude(id__in=exclude_delivery_ids)
            .values_list("bread_id", "subscription__member_id")
        )
        if not choices:
            return Counter()

        cls.warm_caches_for_week(year, delivery_week, choices[0][1], cache=cache)
        delivery_days = TapirCache.get_delivery_day_by_pickup_location_id(cache=cache)
        counts = Counter()
        for bread_id, member_id in choices:
            if cls._has_member_taken_joker(member_id, year, delivery_week, cache=cache):
                continue
            pickup_location_id = cls._get_member_pickup_location_id(
                member_id, year, delivery_week, cache=cache
            )
            if (
                pickup_location_id is not None
                and delivery_days.get(pickup_location_id) == delivery_day
            ):
                counts[bread_id] += 1
        return counts

    @classmethod
    def get_deliveries_by_location_for_week(
        cls,
        year: int,
        delivery_week: int,
        cache: dict,
        queryset=None,
        include_jokered: bool = False,
        delivery_day: int | None = None,
    ) -> dict:
        """
        The week's deliveries grouped by the pickup location they resolve to.

        Deliveries whose member has no pickup location at that date are
        dropped, as are jokered ones unless asked for: a jokered slot is not
        delivered.
        """
        if queryset is None:
            grouped = get_from_cache_or_compute(
                get_from_cache_or_compute(
                    cache, "bread_deliveries_by_location", lambda: {}
                ),
                (year, delivery_week, include_jokered),
                lambda: cls._group_deliveries_by_location(
                    BreadDelivery.objects.all(),
                    year,
                    delivery_week,
                    cache,
                    include_jokered,
                ),
            )
        else:
            grouped = cls._group_deliveries_by_location(
                queryset, year, delivery_week, cache, include_jokered
            )

        if delivery_day is None:
            return grouped

        delivery_days = TapirCache.get_delivery_day_by_pickup_location_id(cache=cache)

        for pickup_location_id, deliveries in grouped.items():
            if delivery_days.get(pickup_location_id) is None:
                logger.warning(
                    "Pickup location %s has no opening times, so its %d bread "
                    "delivery slots in week %d/%d appear on no list. Set at "
                    "least one opening day.",
                    pickup_location_id,
                    len(deliveries),
                    delivery_week,
                    year,
                )

        return {
            pickup_location_id: deliveries
            for pickup_location_id, deliveries in grouped.items()
            if delivery_days.get(pickup_location_id) == delivery_day
        }

    @classmethod
    def _group_deliveries_by_location(
        cls, queryset, year, delivery_week, cache, include_jokered
    ):
        deliveries = list(
            queryset.filter(year=year, delivery_week=delivery_week).select_related(
                "bread", "subscription__member"
            )
        )
        if not deliveries:
            return {}

        cls._warm_member_caches(
            deliveries[0].subscription.member_id, cache, include_jokered
        )

        deliveries_by_location = {}
        for delivery in deliveries:
            if not include_jokered and cls.is_joker_taken(delivery, cache=cache):
                continue
            pickup_location_id = cls.get_pickup_location_id(delivery, cache=cache)
            if pickup_location_id is None:
                continue
            deliveries_by_location.setdefault(pickup_location_id, []).append(delivery)

        return deliveries_by_location

    @classmethod
    def warm_caches_for_week(
        cls, year: int, delivery_week: int, any_member_id, cache: dict
    ):
        """
        Loads what count_chosen_breads_for_delivery_day looks up for every
        member, so a caller can do it before taking row locks.
        """
        cls.get_reference_date(year, delivery_week, cache=cache)
        cls._warm_member_caches(any_member_id, cache, include_jokered=False)
        TapirCache.get_delivery_day_by_pickup_location_id(cache=cache)

    @classmethod
    def _warm_member_caches(cls, any_member_id, cache: dict, include_jokered: bool):
        """
        Loads the jokers and the members' pickup locations for the whole
        batch at once; the return values are unused. The jokers only when
        jokered slots are to be left out.
        """
        if not include_jokered:
            TapirCache.get_all_jokers_for_member(member_id=any_member_id, cache=cache)
        MemberPickupLocationGetter.get_member_pickup_locations_objects_by_member_id(
            cache=cache
        )

    @classmethod
    def get_deliveries_for_location_for_week(
        cls,
        year: int,
        delivery_week: int,
        pickup_location_id: str,
        cache: dict,
        queryset=None,
        include_jokered: bool = False,
    ) -> list:
        return cls.get_deliveries_by_location_for_week(
            year=year,
            delivery_week=delivery_week,
            cache=cache,
            queryset=queryset,
            include_jokered=include_jokered,
        ).get(pickup_location_id, [])
