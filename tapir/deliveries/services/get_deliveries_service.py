import datetime
from typing import Dict, Set

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.deliveries.services.weeks_without_delivery_service import (
    WeeksWithoutDeliveryService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.models import (
    PickupLocationOpeningTime,
    Member,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date


class GetDeliveriesService:
    @classmethod
    def get_deliveries(
        cls,
        member: Member,
        date_from: datetime.date,
        date_to: datetime.date,
        cache: Dict,
    ):
        deliveries = []

        next_delivery_date = get_next_delivery_date(date_from, cache=cache)
        while next_delivery_date <= date_to:
            delivery_object = cls.build_delivery_object(
                member=member, delivery_date=next_delivery_date, cache=cache
            )
            if delivery_object:
                deliveries.append(delivery_object)

            next_delivery_date = get_next_delivery_date(
                get_monday(next_delivery_date + datetime.timedelta(days=7)), cache=cache
            )

        return deliveries

    @classmethod
    def build_delivery_object(
        cls, member: Member, delivery_date: datetime.date, cache: Dict
    ):
        _, week_num, _ = delivery_date.isocalendar()
        even_week = week_num % 2 == 0

        relevant_subscriptions = cls.get_relevant_subscriptions(
            member=member,
            reference_date=delivery_date,
            even_week=even_week,
            cache=cache,
        )

        if len(relevant_subscriptions) == 0:
            return None

        pickup_location = member.get_pickup_location(delivery_date)
        opening_times = PickupLocationOpeningTime.objects.filter(
            pickup_location=pickup_location
        )
        delivery_date = cls.update_delivery_date_to_opening_times(
            opening_times, delivery_date
        )

        joker_used = cls.is_joker_used_in_week(member, delivery_date, cache=cache)

        if joker_used:
            relevant_subscriptions = set(
                filter(
                    lambda subscription: not JokerManagementService.is_subscription_affected_by_joker(
                        subscription,
                        cache=cache,
                    ),
                    relevant_subscriptions,
                )
            )

        return {  # data for DeliverySerializer
            "delivery_date": delivery_date,
            "pickup_location": pickup_location,
            "pickup_location_opening_times": opening_times,
            "subscriptions": relevant_subscriptions,
            "joker_used": joker_used,
            "can_joker_be_used": JokerManagementService.can_joker_be_used_in_week(
                member,
                delivery_date,
                cache=cache,
            ),
            "can_joker_be_used_relative_to_date_limit": JokerManagementService.can_joker_be_used_relative_to_date_limit(
                delivery_date,
                cache=cache,
            ),
            "is_delivery_cancelled_this_week": WeeksWithoutDeliveryService.is_delivery_cancelled_this_week(
                delivery_date,
                cache=cache,
            ),
        }

    @classmethod
    def get_relevant_subscriptions(
        cls, member: Member, reference_date: datetime.date, even_week: bool, cache: Dict
    ) -> Set[Subscription]:
        accepted_delivery_cycles = [
            WEEKLY[0],
            EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
        ]
        subscriptions_with_accepted_delivery_cycles = set()
        for delivery_cycle in accepted_delivery_cycles:
            subscriptions_with_accepted_delivery_cycles.update(
                TapirCache.get_subscriptions_by_delivery_cycle(
                    cache=cache, delivery_cycle=delivery_cycle
                )
            )

        def subscription_filter(subscription: Subscription):
            return (
                subscription.member_id == member.id
                and subscription in subscriptions_with_accepted_delivery_cycles
            )

        return AutomaticSubscriptionRenewalService.get_subscriptions_and_renewals(
            reference_date=reference_date,
            cache=cache,
            subscription_filter=subscription_filter,
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
        cls, member: Member, delivery_date: datetime.date, cache: Dict
    ) -> bool:
        if not get_parameter_value(ParameterKeys.JOKERS_ENABLED, cache=cache):
            return False

        week_start = get_monday(delivery_date)
        week_end = week_start + datetime.timedelta(days=6)
        return Joker.objects.filter(
            member=member, date__gte=week_start, date__lte=week_end
        ).exists()
