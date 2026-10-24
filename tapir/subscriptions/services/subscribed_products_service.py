from tapir.wirgarten.models import Member
from tapir.wirgarten.service.products import get_active_and_future_subscriptions


class SubscribedProductsService:
    @classmethod
    def get_subscribed_products(cls, member: Member, cache: dict):
        return {
            subscription.product
            for subscription in cls.get_relevant_subscriptions(
                member=member, cache=cache
            ).select_related("product")
        }

    @classmethod
    def get_relevant_subscriptions(cls, member: Member, cache: dict):
        return get_active_and_future_subscriptions(cache=cache).filter(
            member=member, cancellation_ts__isnull=True
        )
