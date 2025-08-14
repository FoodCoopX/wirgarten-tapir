import datetime
from decimal import Decimal
from typing import Dict

from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
)
from tapir.wirgarten.models import Member, Subscription, GrowingPeriod
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.products import get_active_subscriptions, get_product_price


class DeliveryPriceCalculator:
    @classmethod
    def get_price_of_subscriptions_delivered_in_week(
        cls,
        member: Member,
        reference_date: datetime.date,
        only_subscriptions_affected_by_jokers: bool,
        cache: Dict,
    ):
        subscriptions = cls.get_subscriptions_that_get_delivered_in_week(
            member, reference_date, cache=cache
        )
        if only_subscriptions_affected_by_jokers:
            subscriptions = subscriptions.filter(
                product__type__is_affected_by_jokers=True
            )
        return sum(
            [
                cls.get_price_of_single_delivery_without_solidarity(
                    subscription, reference_date, cache=cache
                )
                * subscription.quantity
                for subscription in subscriptions
            ]
        )

    @classmethod
    def get_subscriptions_that_get_delivered_in_week(
        cls, member: Member, reference_date: datetime.date, cache: Dict
    ):
        subscriptions = get_active_subscriptions(reference_date).filter(member=member)
        accepted_delivery_cycles = DeliveryCycleService.get_cycles_delivered_in_week(
            date=reference_date, cache=cache
        )
        return subscriptions.filter(
            product__type__delivery_cycle__in=accepted_delivery_cycles
        )

    @classmethod
    def get_price_of_single_delivery_without_solidarity(
        cls, subscription: Subscription, at_date: datetime.date, cache: dict
    ) -> Decimal:
        product_price = get_product_price(
            subscription.product, at_date, cache=cache
        ).price
        delivery_price = product_price * 12 / 52
        if (
            subscription.product.type.delivery_cycle == ODD_WEEKS[0]
            or subscription.product.type.delivery_cycle == EVEN_WEEKS[0]
        ):
            delivery_price *= 2
        elif subscription.product.type.delivery_cycle == EVERY_FOUR_WEEKS[0]:
            delivery_price += 4
        return delivery_price

    @classmethod
    def get_number_of_deliveries_in_growing_period(
        cls, growing_period: GrowingPeriod, delivery_cycle, cache: Dict
    ) -> int:
        if delivery_cycle == NO_DELIVERY[0]:
            return 0

        count = 0
        current_date = get_next_delivery_date(growing_period.start_date, cache=cache)
        while current_date <= growing_period.end_date:
            if DeliveryCycleService.is_cycle_delivered_in_week(
                cycle=delivery_cycle, date=current_date, cache=cache
            ):
                count += 1

            current_date = get_next_delivery_date(
                get_monday(current_date + datetime.timedelta(days=7)), cache=cache
            )

        return count

    @classmethod
    def get_number_of_months_in_growing_period(
        cls, growing_period: GrowingPeriod
    ) -> int:
        return round((growing_period.end_date - growing_period.start_date).days / 30)
