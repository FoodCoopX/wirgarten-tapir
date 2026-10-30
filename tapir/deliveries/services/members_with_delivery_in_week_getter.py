import datetime

from django.db.models import QuerySet

from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday, get_next_sunday
from tapir.wirgarten.models import Member, ProductType
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date


class MembersWithDeliveryInWeekGetter:
    @classmethod
    def get_members_with_delivery_in_week(
        cls,
        product_type: ProductType | None,
        reference_date: datetime.date,
        cache: dict,
    ) -> QuerySet[Member]:
        delivery_date = get_next_delivery_date(
            reference_date=get_monday(reference_date), cache=cache
        )

        # Only weeks fully covered by the subscription get delivered, see GetDeliveriesService.get_relevant_subscriptions
        subscriptions = TapirCache.get_subscriptions_active_at_date(
            reference_date=get_next_sunday(delivery_date), cache=cache
        )

        member_ids = {
            subscription.member_id
            for subscription in subscriptions
            if (product_type is None or subscription.product.type_id == product_type.id)
            and SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
                subscription=subscription,
                delivery_date=delivery_date,
                cache=cache,
                skip_donation_check=False,
            )
        }

        return Member.objects.filter(id__in=member_ids)
