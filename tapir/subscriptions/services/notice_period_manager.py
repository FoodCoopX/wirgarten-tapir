from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.models import NoticePeriod
from tapir.wirgarten.models import ProductType, GrowingPeriod
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
