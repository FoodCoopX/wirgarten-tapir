import datetime
from decimal import Decimal

from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS, NO_DELIVERY
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
    ):
        subscriptions = cls.get_subscriptions_that_get_delivered_in_week(
            member, reference_date
        )
        if only_subscriptions_affected_by_jokers:
            subscriptions = subscriptions.filter(
                product__type__is_affected_by_jokers=True
            )
        return sum(
            [
                cls.get_price_of_single_delivery_without_solidarity(
                    subscription, reference_date
                )
                * subscription.quantity
                for subscription in subscriptions
            ]
        )

    @classmethod
    def get_subscriptions_that_get_delivered_in_week(
        cls, member: Member, reference_date: datetime.date
    ):
        calendar_week = reference_date.isocalendar().week
        even_week = calendar_week % 2 == 0

        subscriptions = get_active_subscriptions(reference_date).filter(member=member)
        return subscriptions.filter(
            product__type__delivery_cycle__in=[
                WEEKLY[0],
                EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
            ]
        )

    @classmethod
    def get_price_of_single_delivery_without_solidarity(
        cls, subscription: Subscription, at_date: datetime.date
    ) -> Decimal:
        product_price = get_product_price(subscription.product, at_date).price
        return product_price * 12 / 52

    @classmethod
    def get_number_of_deliveries_in_growing_period(
        cls, growing_period: GrowingPeriod, delivery_cycle
    ) -> int:
        if delivery_cycle == NO_DELIVERY[0]:
            return 0

        count = 0
        current_date = get_next_delivery_date(growing_period.start_date)
        while current_date <= growing_period.end_date:
            calendar_week = current_date.isocalendar().week
            even_week = calendar_week % 2 == 0

            if (
                delivery_cycle == WEEKLY[0]
                or delivery_cycle == EVEN_WEEKS[0]
                and even_week
                or delivery_cycle == ODD_WEEKS[0]
                and not even_week
            ):
                count += 1

            current_date = get_next_delivery_date(
                get_monday(current_date + datetime.timedelta(days=7))
            )

        return count

    @classmethod
    def get_number_of_months_in_growing_period(
        cls, growing_period: GrowingPeriod
    ) -> int:
        return round((growing_period.end_date - growing_period.start_date).days / 30)
