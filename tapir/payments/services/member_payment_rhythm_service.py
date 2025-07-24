import datetime

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ImproperlyConfigured

from tapir.payments.models import MemberPaymentRhythm
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member


class MemberPaymentRhythmService:
    @staticmethod
    def get_member_payment_rhythm(
        member: Member, reference_date: datetime.date, cache: dict
    ):
        rhythm_object = TapirCache.get_member_payment_rhythm_object(
            member=member, reference_date=reference_date, cache=cache
        )
        if rhythm_object is None:
            return MemberPaymentRhythm.Rhythm.MONTHLY
        return rhythm_object.rhythm

    @classmethod
    def should_generate_payment_at_date(
        cls, rhythm, reference_date: datetime.date, cache: dict
    ) -> bool:
        months_with_generation = cls.get_months_where_payments_should_be_generated(
            rhythm
        )
        month_index = cls.get_month_index_relative_to_growing_period(
            reference_date=reference_date, cache=cache
        )
        return month_index in months_with_generation

    @classmethod
    def get_months_where_payments_should_be_generated(cls, rhythm):
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
