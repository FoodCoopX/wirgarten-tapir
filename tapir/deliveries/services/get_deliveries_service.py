import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.deliveries.services.weeks_without_delivery_service import (
    WeeksWithoutDeliveryService,
)
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.models import (
    Subscription,
    PickupLocationOpeningTime,
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.products import get_current_growing_period


class GetDeliveriesService:
    @classmethod
    def get_deliveries(
        cls,
        member: Member,
        date_from: datetime.date,
        date_to: datetime.date,
    ):
        deliveries = []

        next_delivery_date = get_next_delivery_date(date_from)
        while next_delivery_date <= date_to:
            delivery_object = cls.build_delivery_object(member, next_delivery_date)
            if delivery_object:
                deliveries.append(delivery_object)

            next_delivery_date = get_next_delivery_date(
                get_monday(next_delivery_date + datetime.timedelta(days=7))
            )

        return deliveries

    @classmethod
    def build_delivery_object(cls, member: Member, delivery_date: datetime.date):
        _, week_num, _ = delivery_date.isocalendar()
        even_week = week_num % 2 == 0

        relevant_subscriptions = cls.get_relevant_subscriptions(
            member=member, reference_date=delivery_date, even_week=even_week
        )

        if not relevant_subscriptions.exists():
            if not get_parameter_value(ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL):
                return None
            current_growing_period = get_current_growing_period(delivery_date)
            relevant_subscriptions = cls.get_relevant_subscriptions(
                member=member,
                reference_date=current_growing_period.start_date
                - datetime.timedelta(days=1),
                even_week=even_week,
            )
            relevant_subscriptions = relevant_subscriptions.filter(
                cancellation_ts__isnull=True,
            )
            if not relevant_subscriptions.exists():
                return None

        pickup_location = member.get_pickup_location(delivery_date)
        opening_times = PickupLocationOpeningTime.objects.filter(
            pickup_location=pickup_location
        )
        delivery_date = cls.update_delivery_date_to_opening_times(
            opening_times, delivery_date
        )

        joker_used = cls.is_joker_used_in_week(member, delivery_date)

        if joker_used:
            relevant_subscriptions = relevant_subscriptions.filter(
                product__type__is_affected_by_jokers=False
            )

        return {  # data for DeliverySerializer
            "delivery_date": delivery_date,
            "pickup_location": pickup_location,
            "pickup_location_opening_times": opening_times,
            "subscriptions": relevant_subscriptions,
            "joker_used": joker_used,
            "can_joker_be_used": JokerManagementService.can_joker_be_used_in_week(
                member, delivery_date
            ),
            "can_joker_be_used_relative_to_date_limit": JokerManagementService.can_joker_be_used_relative_to_date_limit(
                delivery_date
            ),
            "is_delivery_cancelled_this_week": WeeksWithoutDeliveryService.is_delivery_cancelled_this_week(
                delivery_date
            ),
        }

    @classmethod
    def get_relevant_subscriptions(
        cls, member: Member, reference_date: datetime.date, even_week: bool
    ):
        return Subscription.objects.filter(
            member=member,
            start_date__lte=reference_date,
            end_date__gte=reference_date,
            product__type__delivery_cycle__in=[
                WEEKLY[0],
                EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
            ],
        )

    @classmethod
    def update_delivery_date_to_opening_times(
        cls, opening_times, delivery_date: datetime.date
    ):
        delivery_date += datetime.timedelta(
            days=(
                opening_times[0].day_of_week - delivery_date.weekday()
                if opening_times
                else 0
            )
        )
        return delivery_date

    @classmethod
    def is_joker_used_in_week(
        cls, member: Member, delivery_date: datetime.date
    ) -> bool:
        if not get_parameter_value(ParameterKeys.JOKERS_ENABLED):
            return False

        week_start = get_monday(delivery_date)
        week_end = week_start + datetime.timedelta(days=6)
        return Joker.objects.filter(
            member=member, date__gte=week_start, date__lte=week_end
        ).exists()
