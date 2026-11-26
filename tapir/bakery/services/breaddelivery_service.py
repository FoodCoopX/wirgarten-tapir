from collections import defaultdict
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import models

from tapir.bakery.models import AvailableBreadsForDeliveryDay, BreadDelivery
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.services.direct_order_limit_service import (
    DirectOrderLimitService,
)
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import GrowingPeriod, Member, Subscription


class BreadDeliveryService:
    """
    Keeps a member's BreadDelivery rows in step with their subscriptions: one
    row per delivered week per slot, and no row for a week they are not
    delivered in.
    """

    @classmethod
    def get_weeks_in_range(cls, start_date, end_date):
        """
        Strides from the Monday of the first week, so that the last ISO week is
        still yielded when end_date falls on an earlier weekday than start_date.
        """
        if end_date < start_date:
            return

        current_date = start_date - timedelta(days=start_date.weekday())
        while current_date <= end_date:
            iso_calendar = current_date.isocalendar()
            yield (iso_calendar[0], iso_calendar[1])
            current_date += timedelta(weeks=1)

    @classmethod
    def ensure_bread_deliveries_for_member(
        cls, member: Member, cache: dict | None = None
    ):
        if cache is None:
            cache = {}

        if not settings.BAKERY_ENABLED:
            return

        cls._sync_deliveries(member, cache=cache)

    @classmethod
    def resync_bread_deliveries_for_growing_period(cls, growing_period: GrowingPeriod):
        """
        weeks_without_delivery is honoured at write time, so editing it on an
        existing growing period has to rewrite the rows already created.
        """
        cache = {}
        if not settings.BAKERY_ENABLED:
            return

        member_ids = (
            Subscription.objects.filter(
                start_date__lte=growing_period.end_date,
                end_date__gte=growing_period.start_date,
            )
            .values_list("member_id", flat=True)
            .distinct()
        )

        for member in Member.objects.filter(id__in=list(member_ids)):
            cls.ensure_bread_deliveries_for_member(member, cache=cache)

    @classmethod
    def clear_breads_unavailable_at_pickup_location(
        cls,
        member: Member,
        previous_pickup_location_id: str | None,
        valid_from: date,
        cache: dict,
    ):
        """
        After the member changed pickup location, drop the bread choices it
        cannot supply: a pickup location offers the breads baked on its
        delivery day. A choice the change moves to another delivery day must
        also fit that day's direct-order limits like a new choice; one that
        stays on its day keeps its place, as existing orders do when a limit
        is lowered.

        Only current and future weeks: past deliveries are a record of what was
        handed over.
        """
        if not settings.BAKERY_ENABLED:
            return

        now = datetime.now().date()
        current_year, current_week, _ = now.isocalendar()

        deliveries = list(
            BreadDelivery.objects.filter(
                subscription__member=member, bread__isnull=False
            )
            .filter(
                models.Q(year__gt=current_year)
                | models.Q(year=current_year, delivery_week__gte=current_week)
            )
            .select_related("subscription")
        )
        if not deliveries:
            return

        weeks = {(delivery.year, delivery.delivery_week) for delivery in deliveries}
        available = set(
            AvailableBreadsForDeliveryDay.objects.filter(
                year__in={year for year, _ in weeks},
                delivery_week__in={week for _, week in weeks},
                bread__is_active=True,
            ).values_list("year", "delivery_week", "delivery_day", "bread_id")
        )
        delivery_days = TapirCache.get_delivery_day_by_pickup_location_id(cache=cache)
        previous_delivery_day = delivery_days.get(previous_pickup_location_id)

        to_clear = []
        moved_by_day = defaultdict(list)
        for delivery in deliveries:
            pickup_location_id = BreadDeliveryContextService.get_pickup_location_id(
                delivery, cache=cache
            )
            delivery_day = delivery_days.get(pickup_location_id)
            key = (
                delivery.year,
                delivery.delivery_week,
                delivery_day,
                delivery.bread_id,
            )
            if key not in available:
                to_clear.append(delivery)
            elif (
                cls._is_moved_to_another_day(
                    delivery, delivery_day, previous_delivery_day, valid_from, cache
                )
                and not BreadDeliveryContextService.is_joker_taken(
                    delivery, cache=cache
                )
                and not BreadChoiceDeadlineService.is_delivery_day_over(
                    delivery.year, delivery.delivery_week, delivery_day, cache=cache
                )
            ):
                moved_by_day[
                    (delivery.year, delivery.delivery_week, delivery_day)
                ].append(delivery)

        for (year, delivery_week, delivery_day), moved in moved_by_day.items():
            to_clear.extend(
                cls._choices_over_the_limit(
                    moved, year, delivery_week, delivery_day, cache=cache
                )
            )

        for delivery in to_clear:
            delivery.bread = None
        if to_clear:
            BreadDelivery.objects.bulk_update(to_clear, ["bread"])

    @classmethod
    def _is_moved_to_another_day(
        cls,
        delivery: BreadDelivery,
        delivery_day: int | None,
        previous_delivery_day: int | None,
        valid_from: date,
        cache: dict,
    ) -> bool:
        """
        Whether the change of pickup location puts the delivery on another
        delivery day: it applies from valid_from on, the reference date by
        which the delivery's pickup location is resolved.
        """
        reference_date = BreadDeliveryContextService.get_reference_date(
            delivery.year, delivery.delivery_week, cache=cache
        )
        return reference_date >= valid_from and delivery_day != previous_delivery_day

    @classmethod
    def _choices_over_the_limit(
        cls,
        choices: list[BreadDelivery],
        year: int,
        delivery_week: int,
        delivery_day: int,
        cache: dict,
    ) -> list[BreadDelivery]:
        """
        The member's choices of one delivery day that do not fit its limits
        when made one after the other, as if new. Mostly one or two per day.
        """
        accepted = []
        over = []
        for choice in sorted(choices, key=lambda delivery: delivery.slot_number):
            limits = DirectOrderLimitService.get_limits_for_day(
                year=year,
                delivery_week=delivery_week,
                delivery_day=delivery_day,
                cache=cache,
                exclude_delivery_ids=[
                    delivery.id for delivery in choices if delivery not in accepted
                ],
            )
            remaining = limits.remaining(choice.bread_id)
            if remaining is not None and remaining <= 0:
                over.append(choice)
            else:
                accepted.append(choice)
        return over

    @classmethod
    def get_choices_of_breads_for_delivery_day(
        cls,
        bread_ids: list,
        year: int,
        delivery_week: int,
        delivery_day: int,
        cache: dict,
    ) -> list[BreadDelivery]:
        """
        The slots where members chose one of the breads for that delivery day,
        at every pickup location delivered that day, jokered ones included. Nothing
        once the day is over (see BreadChoiceDeadlineService.is_delivery_day_over).
        """
        if not bread_ids or BreadChoiceDeadlineService.is_delivery_day_over(
            year, delivery_week, delivery_day, cache=cache
        ):
            return []

        deliveries_by_location = (
            BreadDeliveryContextService.get_deliveries_by_location_for_week(
                year=year,
                delivery_week=delivery_week,
                cache=cache,
                queryset=BreadDelivery.objects.filter(bread_id__in=bread_ids),
                include_jokered=True,
                delivery_day=delivery_day,
            )
        )
        return [
            delivery
            for deliveries in deliveries_by_location.values()
            for delivery in deliveries
        ]

    @classmethod
    def clear_choices_of_breads_for_delivery_day(
        cls,
        bread_ids: list,
        year: int,
        delivery_week: int,
        delivery_day: int,
        cache: dict,
    ) -> int:
        """
        For breads no longer baked on that delivery day: drops the choices
        get_choices_of_breads_for_delivery_day finds and returns how many.
        The update checks the bread again: a member who switched to another
        bread since the read keeps that choice.
        """
        deliveries = cls.get_choices_of_breads_for_delivery_day(
            bread_ids, year, delivery_week, delivery_day, cache=cache
        )
        return BreadDelivery.objects.filter(
            id__in=[delivery.id for delivery in deliveries],
            bread_id__in=bread_ids,
        ).update(bread=None)

    @classmethod
    def _sync_deliveries(cls, member: Member, cache: dict):
        now = datetime.now().date()
        current_iso = now.isocalendar()
        current_year, current_week = current_iso[0], current_iso[1]

        cls._sync_relevant_subscriptions(member, now, cache=cache)
        cls._cleanup_expired_subscriptions(member, now, current_year, current_week)

    @classmethod
    def _sync_relevant_subscriptions(cls, member, now, cache: dict):
        relevant_subscriptions = Subscription.objects.filter(
            member=member,
            end_date__gte=now,
        ).select_related("product__type")

        for subscription in relevant_subscriptions:
            if not subscription.start_date or not subscription.end_date:
                continue

            cls._sync_subscription_deliveries(subscription, cache=cache)

    @classmethod
    def _delivered_weeks_in_period(cls, subscription, cache: dict) -> list:
        """
        The ISO weeks this subscription is actually delivered in.

        Filtered on the week's real delivery date rather than the week itself,
        which is how core's GetDeliveriesService counts deliveries.
        """
        weeks = []
        for year, week in cls.get_weeks_in_range(
            subscription.start_date, subscription.end_date
        ):
            delivery_date = BreadDeliveryContextService.get_reference_date(
                year, week, cache=cache
            )
            if not subscription.start_date <= delivery_date <= subscription.end_date:
                continue
            if not DeliveryDateCalculator.is_week_delivered(
                product_type=subscription.product.type,
                delivery_date=delivery_date,
                check_for_weeks_without_delivery=True,
                cache=cache,
            ):
                continue
            weeks.append((year, week))

        return weeks

    @classmethod
    def _sync_subscription_deliveries(cls, subscription, cache: dict):
        """Brings the rows to exactly one per delivered week per slot."""
        target_quantity = subscription.quantity

        weeks_in_period = cls._delivered_weeks_in_period(subscription, cache=cache)
        valid_year_weeks = set(weeks_in_period)

        existing_by_week = {}
        for delivery in BreadDelivery.objects.filter(
            subscription=subscription
        ).order_by("slot_number"):
            existing_by_week.setdefault(
                (delivery.year, delivery.delivery_week), []
            ).append(delivery)

        to_delete = []
        to_renumber = []
        to_create = []

        for year_week, deliveries in existing_by_week.items():
            if year_week not in valid_year_weeks:
                to_delete.extend(deliveries)

        for year, week in weeks_in_period:
            existing = existing_by_week.get((year, week), [])

            # The slots must come out as exactly 1..target_quantity, with no gaps.
            to_delete.extend(existing[target_quantity:])
            kept = existing[:target_quantity]

            for slot_number, delivery in enumerate(kept, start=1):
                if delivery.slot_number != slot_number:
                    # Renumbering rather than deleting keeps the member's bread
                    # choice.
                    delivery.slot_number = slot_number
                    to_renumber.append(delivery)

            for slot_number in range(len(kept) + 1, target_quantity + 1):
                to_create.append(
                    BreadDelivery(
                        subscription=subscription,
                        year=year,
                        delivery_week=week,
                        slot_number=slot_number,
                        bread=None,
                    )
                )

        if to_delete:
            BreadDelivery.objects.filter(
                id__in=[delivery.id for delivery in to_delete]
            ).delete()
        if to_renumber:
            # One statement per row, ascending: the unique constraint on
            # (subscription, year, delivery_week, slot_number) is checked per
            # row, so a single bulk_update could fire on an intermediate state.
            for delivery in sorted(to_renumber, key=lambda d: d.slot_number):
                delivery.save(update_fields=["slot_number"])
        if to_create:
            BreadDelivery.objects.bulk_create(to_create)

    @classmethod
    def _cleanup_expired_subscriptions(cls, member, now, current_year, current_week):
        BreadDelivery.objects.filter(
            subscription__member=member,
            subscription__end_date__lt=now,
        ).filter(
            models.Q(year__gt=current_year)
            | models.Q(year=current_year, delivery_week__gt=current_week)
        ).delete()
