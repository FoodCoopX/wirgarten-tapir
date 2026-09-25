from datetime import datetime, timedelta

from django.db import models
from django.db.utils import OperationalError, ProgrammingError

from tapir.bakery.models import BreadCapacityPickupLocation, BreadDelivery
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.wirgarten.models import GrowingPeriod, Member, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys


class BreadDeliveryService:
    """
    Keeps a member's BreadDelivery rows in step with their subscriptions: one
    row per delivered week per slot, and no row for a week they are not
    delivered in.
    """

    @classmethod
    def is_bakery_enabled(cls, cache: dict | None = None) -> bool:
        """
        Non-throwing: get_parameter_value raises when the parameter row has not
        been seeded, and this runs from a post_save receiver.
        """
        try:
            return bool(get_parameter_value(ParameterKeys.BAKERY_ENABLED, cache=cache))
        except (KeyError, ProgrammingError, OperationalError):
            return False

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

        if not cls.is_bakery_enabled(cache=cache):
            return

        cls._sync_deliveries(member, cache=cache)

    @classmethod
    def resync_bread_deliveries_for_growing_period(cls, growing_period: GrowingPeriod):
        """
        weeks_without_delivery is honoured at write time, so editing it on an
        existing growing period has to rewrite the rows already created.
        """
        cache = {}
        if not cls.is_bakery_enabled(cache=cache):
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
        cls, member: Member, cache: dict | None = None
    ):
        """
        Drop bread choices the member's station cannot supply any more.

        Only current and future weeks: past deliveries are a record of what was
        handed over.
        """
        if cache is None:
            cache = {}
        if not cls.is_bakery_enabled(cache=cache):
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
            BreadCapacityPickupLocation.objects.filter(
                year__in={year for year, _ in weeks},
                delivery_week__in={week for _, week in weeks},
            ).values_list("year", "delivery_week", "pickup_location_id", "bread_id")
        )

        to_clear = []
        for delivery in deliveries:
            pickup_location_id = BreadDeliveryContextService.get_pickup_location_id(
                delivery, cache=cache
            )
            key = (
                delivery.year,
                delivery.delivery_week,
                pickup_location_id,
                delivery.bread_id,
            )
            if key not in available:
                delivery.bread = None
                to_clear.append(delivery)

        if to_clear:
            BreadDelivery.objects.bulk_update(to_clear, ["bread"])

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
