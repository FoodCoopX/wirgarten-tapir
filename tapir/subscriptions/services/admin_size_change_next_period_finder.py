from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import GrowingPeriod, Member, Subscription


class AdminSizeChangeNextPeriodFinder:
    @classmethod
    def get_next_period_with_subscriptions(
        cls, member: Member, subscription: Subscription, cache: dict
    ) -> GrowingPeriod | None:
        next_growing_period = TapirCache.get_first_growing_period_starting_after(
            reference_date=subscription.end_date, cache=cache
        )
        if next_growing_period is None:
            return None

        for other_subscription in TapirCache.get_all_subscriptions_for_member(
            member_id=member.id, cache=cache
        ):
            if (
                other_subscription.product.type_id == subscription.product.type_id
                and other_subscription.start_date >= next_growing_period.start_date
                and other_subscription.cancellation_ts is None
            ):
                return next_growing_period

        return None
