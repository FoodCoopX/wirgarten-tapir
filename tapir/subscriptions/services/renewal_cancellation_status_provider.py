from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class RenewalCancellationStatusProvider:
    STATUS_AVAILABLE = "available"
    STATUS_BEFORE_NOTICE_PERIOD_END = "before_notice_period_end"
    STATUS_NOT_AVAILABLE = "not_available"
    STATUSES = [STATUS_AVAILABLE, STATUS_BEFORE_NOTICE_PERIOD_END, STATUS_NOT_AVAILABLE]

    @classmethod
    def get_status(cls, subscription: Subscription, cache: dict) -> str:
        if not get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
        ):
            return cls.STATUS_NOT_AVAILABLE

        if cls.get_renewal(subscription=subscription, cache=cache) is not None:
            return cls.STATUS_AVAILABLE

        if subscription.cancellation_ts is not None:
            return cls.STATUS_NOT_AVAILABLE

        if NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription=subscription, cache=cache
        ) >= get_today(cache=cache):
            return cls.STATUS_BEFORE_NOTICE_PERIOD_END

        if (
            TapirCache.get_first_growing_period_starting_after(
                reference_date=subscription.end_date, cache=cache
            )
            is None
        ):
            return cls.STATUS_NOT_AVAILABLE

        return cls.STATUS_AVAILABLE

    @classmethod
    def get_renewal(
        cls, subscription: Subscription, cache: dict
    ) -> Subscription | None:
        later_subscriptions = [
            other_subscription
            for other_subscription in TapirCache.get_all_subscriptions_for_member(
                member_id=subscription.member_id, cache=cache
            )
            if other_subscription.product_id == subscription.product_id
            and other_subscription.start_date > subscription.end_date
        ]
        # A follow-up contract in the same growing period (e.g. after a mid-period order change) carries the renewal
        if any(
            later_subscription.start_date <= subscription.period.end_date
            for later_subscription in later_subscriptions
        ):
            return None
        return min(
            later_subscriptions,
            key=lambda later_subscription: later_subscription.start_date,
            default=None,
        )
