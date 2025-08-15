import datetime

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.models import MemberPaymentRhythm
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys


class MemberPaymentRhythmService:
    @staticmethod
    def get_member_payment_rhythm(
        member: Member, reference_date: datetime.date, cache: dict
    ):
        rhythm_object = TapirCache.get_member_payment_rhythm_object(
            member=member, reference_date=reference_date, cache=cache
        )
        if rhythm_object is None:
            return get_parameter_value(
                ParameterKeys.PAYMENT_DEFAULT_RHYTHM, cache=cache
            )
        return rhythm_object.rhythm

    @classmethod
    def is_start_of_rhythm_period(
        cls, rhythm, reference_date: datetime.date, cache: dict
    ) -> bool:
        months_with_generation = cls.get_month_index_where_payments_should_be_created(
            rhythm
        )
        month_index = cls.get_month_index_relative_to_growing_period(
            reference_date=reference_date, cache=cache
        )
        return month_index in months_with_generation

    @classmethod
    def get_month_index_where_payments_should_be_created(cls, rhythm):
        match rhythm:
            case MemberPaymentRhythm.Rhythm.MONTHLY:
                return range(1, 13)
            case MemberPaymentRhythm.Rhythm.QUARTERLY:
                return [1, 4, 7, 10]
            case MemberPaymentRhythm.Rhythm.SEMIANNUALLY:
                return [1, 7]
            case MemberPaymentRhythm.Rhythm.YEARLY:
                return [1]
            case _:
                raise ImproperlyConfigured(f"Unknown payment rhythm: {rhythm}")

    @classmethod
    def get_month_index_relative_to_growing_period(
        cls, reference_date: datetime.date, cache: dict
    ):
        reference_date = reference_date.replace(day=1)
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_date, cache=cache
        )
        return relativedelta(reference_date, growing_period.start_date).months + 1

    @classmethod
    def get_number_of_months_paid_in_advance(cls, rhythm):
        match rhythm:
            case MemberPaymentRhythm.Rhythm.MONTHLY:
                return 1
            case MemberPaymentRhythm.Rhythm.QUARTERLY:
                return 3
            case MemberPaymentRhythm.Rhythm.SEMIANNUALLY:
                return 6
            case MemberPaymentRhythm.Rhythm.YEARLY:
                return 12
            case _:
                raise ImproperlyConfigured(f"Unknown payment rhythm: {rhythm}")

    @classmethod
    def get_first_day_of_rhythm_period(
        cls, rhythm, reference_date: datetime.date, cache: dict
    ):
        reference_date = reference_date.replace(day=1)
        while not cls.is_start_of_rhythm_period(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        ):
            reference_date = reference_date - relativedelta(months=1)
        return reference_date

    @classmethod
    def get_last_day_of_rhythm_period(
        cls, rhythm, reference_date: datetime.date, cache: dict
    ):
        start = cls.get_first_day_of_rhythm_period(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        )
        return (
            start
            + relativedelta(
                months=cls.get_number_of_months_paid_in_advance(rhythm=rhythm)
            )
            - datetime.timedelta(days=1)
        )
