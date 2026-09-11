import datetime
import logging

from tapir.bakery.models import BreadDelivery
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_from_cache_or_compute, week_to_monday
from tapir.wirgarten.service.delivery import get_next_delivery_date

logger = logging.getLogger(__name__)


class BreadDeliveryContextService:
    """
    Derives a bread delivery's pickup location and joker status.

    Both follow from the member's pickup location history and their jokers, so
    this is the single place that derives them. The codebase has four
    non-equivalent ways to resolve a member's pickup location, and picking a
    different one changes who appears on the Abholliste.
    """

    @classmethod
    def get_reference_date(
        cls, year: int, delivery_week: int, cache: dict
    ) -> datetime.date:
        """
        The date on which a delivery in this ISO week actually happens.

        get_next_delivery_date off the Monday, mirroring
        GetDeliveriesService.build_delivery_object. The raw Monday would
        resolve the pickup location from before a move that takes effect
        mid-week. The result stays inside the same ISO week, so the joker
        lookup - which compares (ISO year, ISO week) - is unaffected.
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
        """
        Requires the delivery to carry its subscription (select_related).

        get_member_pickup_location_id_from_cache specifically: it and
        Member.get_pickup_location share a single-row branch that ignores
        valid_from, which get_member_pickup_location_id and
        get_members_ids_at_pickup_location do not, and the Abholliste depends
        on that branch.
        """
        return MemberPickupLocationService.get_member_pickup_location_id_from_cache(
            member_id=delivery.subscription.member_id,
            reference_date=cls.get_reference_date(
                delivery.year, delivery.delivery_week, cache=cache
            ),
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
        """Requires the delivery to carry its subscription and member."""
        return JokerManagementService.does_member_have_a_joker_in_week(
            member=delivery.subscription.member,
            reference_date=cls.get_reference_date(
                delivery.year, delivery.delivery_week, cache=cache
            ),
            cache=cache,
        )

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
        The primitive every read site goes through: the week's deliveries
        grouped by the pickup location they resolve to.

        Deliveries whose member has no pickup location at that date are
        dropped, as are jokered ones unless asked for - a jokered slot is not
        delivered, so it belongs on neither the Abholliste, the baking plan,
        nor the capacity count.

        delivery_day narrows the result to the stations delivered on that
        weekday.
        """
        if queryset is None:
            # The default shape is cached, so rendering every station of a
            # week - the all-stations PDF - groups the deliveries once.
            grouped = get_from_cache_or_compute(
                get_from_cache_or_compute(
                    cache, "bread_deliveries_by_location", lambda: {}
                ),
                (year, delivery_week, include_jokered),
                lambda: cls._group_deliveries_by_location(
                    BreadDelivery.objects.filter(
                        subscription__product__type__is_bread=True
                    ),
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

        # A station with no PickupLocationOpeningTime rows has no delivery
        # day, so it matches no day and drops off the pickup list, the baking
        # list and the Verteilliste. Every weekday field on the station form is
        # optional, so this is reachable by ordinary admin use: say so rather
        # than dropping its members' bread without a word.
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

        # Two queries for the whole batch rather than one per delivery, scoped
        # to the members that actually appear in it.
        member_ids = {delivery.subscription.member_id for delivery in deliveries}
        TapirCache.get_jokers_by_member_id_for_members(
            member_ids=member_ids, cache=cache
        )
        MemberPickupLocationService.get_member_pickup_locations_objects_for_members(
            member_ids=member_ids, cache=cache
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
