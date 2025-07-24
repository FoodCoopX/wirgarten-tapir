import datetime

from tapir.payments.models import MemberPaymentRhythm
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member


class MemberPaymentRhythmService:
    @staticmethod
    def get_member_payment_rhythm(member: Member, at_date: datetime.date, cache: dict):
        rhythm_object = TapirCache.get_member_payment_rhythm_object(
            member=member, at_date=at_date, cache=cache
        )
        if rhythm_object is None:
            return MemberPaymentRhythm.Rhythm.MONTHLY
        return rhythm_object.rhythm
