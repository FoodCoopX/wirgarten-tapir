import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.models import NoticePeriod
from tapir.wirgarten.models import ProductType, GrowingPeriod, Subscription
from tapir.wirgarten.parameters import Parameter


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
            notice_period.duration_in_months = notice_period_duration
            notice_period.save()
        else:
            NoticePeriod.objects.create(
                product_type=product_type,
                growing_period=growing_period,
                duration_in_months=notice_period_duration,
            )

    @classmethod
    def get_notice_period_duration(
        cls,
        product_type: ProductType,
        growing_period: GrowingPeriod,
    ):
        notice_period = NoticePeriod.objects.filter(
            product_type=product_type,
            growing_period=growing_period,
        ).first()
        if notice_period:
            return notice_period.duration_in_months

        return get_parameter_value(Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD)

    @classmethod
    def get_max_cancellation_date(cls, subscription: Subscription):
        notice_period = cls.get_notice_period_duration(
            product_type=subscription.product.type, growing_period=subscription.period
        )
        max_date = subscription.end_date
        for _ in range(notice_period):
            max_date = max_date.replace(day=1) - datetime.timedelta(days=1)

        return max_date.replace(day=subscription.end_date.day)
