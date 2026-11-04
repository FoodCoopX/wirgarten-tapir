import datetime
from decimal import Decimal

from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.wirgarten.constants import (
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
    CUSTOM_CYCLE,
)
from tapir.wirgarten.models import Member, Subscription, GrowingPeriod
from tapir.wirgarten.service.products import get_active_subscriptions, get_product_price


class DeliveryPriceCalculator:
    @classmethod
    def get_subscriptions_that_get_delivered_in_week(
        cls, member: Member, reference_date: datetime.date, cache: dict
    ):
        subscriptions = (
            get_active_subscriptions(reference_date)
            .filter(member=member)
            .select_related("product__type")
        )

        delivered_subscription_ids = [
            subscription.id
            for subscription in subscriptions
            if DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=subscription.product.type, date=reference_date, cache=cache
            )
        ]

        return subscriptions.filter(id__in=delivered_subscription_ids)

    @classmethod
    def get_price_of_single_delivery_for_subscription(
        cls, subscription: Subscription, at_date: datetime.date, cache: dict
    ) -> Decimal:
        product_price = get_product_price(
            subscription.product, at_date, cache=cache
        ).price

        delivery_cycle = subscription.product.type.delivery_cycle
        if delivery_cycle == CUSTOM_CYCLE[0]:
            return product_price

        return (
            cls.get_price_of_single_delivery_from_monthly_price(
                monthly_price=product_price,
                delivery_cycle=delivery_cycle,
                at_date=at_date,
            )
            * subscription.quantity
        )

    @classmethod
    def get_price_of_single_delivery_from_monthly_price(
        cls, monthly_price: Decimal, delivery_cycle: str, at_date: datetime.date
    ) -> Decimal:
        return (
            monthly_price
            * 12
            / cls.get_number_of_weeks_in_year(at_date.year)
            * cls.get_number_of_weeks_covered_by_single_delivery(delivery_cycle)
        )

    @classmethod
    def get_number_of_weeks_covered_by_single_delivery(cls, delivery_cycle: str) -> int:
        if delivery_cycle in {EVEN_WEEKS[0], ODD_WEEKS[0]}:
            return 2
        if delivery_cycle == EVERY_FOUR_WEEKS[0]:
            return 4
        return 1

    @classmethod
    def get_number_of_months_in_growing_period(
        cls, growing_period: GrowingPeriod
    ) -> int:
        return round((growing_period.end_date - growing_period.start_date).days / 30)

    @classmethod
    def get_number_of_weeks_in_year(cls, year: int):
        # According to this article: https://en.wikipedia.org/wiki/ISO_week_date#Last_week
        # The 28th of December is always the last week of the year,
        # so we can use that property to get the number of weeks in a year
        last_week = datetime.date(year, month=12, day=28)
        return last_week.isocalendar().week
