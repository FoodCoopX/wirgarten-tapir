import calendar
import datetime
from typing import Dict

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions import config as subscription_config
from tapir.subscriptions.models import NoticePeriod
from tapir.wirgarten.models import ProductType, GrowingPeriod, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class NoticePeriodManager:
    @classmethod
    def set_notice_period_duration(
        cls,
        product_type: ProductType,
        growing_period: GrowingPeriod,
        notice_period_duration,
    ):
        notice_period = NoticePeriod.objects.filter(
            product_type=product_type,
            growing_period=growing_period,
        ).first()
        if notice_period:
            notice_period.duration = notice_period_duration
            notice_period.save()
        else:
            NoticePeriod.objects.create(
                product_type=product_type,
                growing_period=growing_period,
                duration=notice_period_duration,
            )

    @classmethod
    def get_notice_period_duration(
        cls,
        product_type: ProductType,
        growing_period: GrowingPeriod,
        cache: Dict,
    ):
        notice_period = NoticePeriod.objects.filter(
            product_type=product_type,
            growing_period=growing_period,
        ).first()
        if notice_period:
            return notice_period.duration

        return get_parameter_value(
            ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD, cache=cache
        )

    @classmethod
    def get_max_cancellation_date(cls, subscription: Subscription, cache: Dict):
        notice_period_duration = subscription.notice_period_duration
        if notice_period_duration is None:
            notice_period_duration = cls.get_notice_period_duration(
                product_type=subscription.product.type,
                growing_period=subscription.period,
                cache=cache,
            )

        match get_parameter_value(
            ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT, cache=cache
        ):
            case subscription_config.NOTICE_PERIOD_UNIT_MONTHS:
                return cls.get_max_cancellation_date_unit_months(
                    subscription=subscription,
                    notice_period_duration=notice_period_duration,
                    cache=cache,
                )
            case subscription_config.NOTICE_PERIOD_UNIT_WEEKS:
                return cls.get_max_cancellation_date_unit_weeks(
                    subscription=subscription,
                    notice_period_duration=notice_period_duration,
                    cache=cache,
                )
            case _:
                raise ImproperlyConfigured(
                    f"Unknown notice period unit: {subscription_config.NOTICE_PERIOD_UNIT_MONTHS}"
                )

    @classmethod
    def get_max_cancellation_date_unit_weeks(
        cls, subscription: Subscription, notice_period_duration: int, cache: Dict
    ):
        if subscription.end_date is None:
            return get_today(cache=cache) + datetime.timedelta(
                days=notice_period_duration * 7
            )

        return subscription.end_date - datetime.timedelta(
            days=notice_period_duration * 7
        )

    @classmethod
    def get_max_cancellation_date_unit_months(
        cls, subscription: Subscription, notice_period_duration: int, cache: Dict
    ):
        if subscription.end_date is None:
            return get_today(cache=cache) + relativedelta(months=notice_period_duration)

        max_date = subscription.end_date
        for _ in range(notice_period_duration):
            max_date = max_date.replace(day=1) - datetime.timedelta(days=1)

        _, nb_days_in_month_subscription_end_date = calendar.monthrange(
            subscription.end_date.year, subscription.end_date.month
        )
        subscription_ends_on_last_day_of_month = (
            nb_days_in_month_subscription_end_date == subscription.end_date.day
        )
        if subscription_ends_on_last_day_of_month:
            return max_date

        _, nb_days_in_month = calendar.monthrange(max_date.year, max_date.month)
        target_day = subscription.end_date.day
        if target_day > nb_days_in_month:
            target_day = nb_days_in_month

        return max_date.replace(day=target_day)
