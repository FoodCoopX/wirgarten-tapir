import datetime

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetMemberPaymentRhythm(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM).update(
            value=MemberPaymentRhythm.Rhythm.YEARLY
        )

    def test_getMemberPaymentRhythm_memberHasARhythmObjectAtDate_returnsRhythmFromObject(
        self,
    ):
        member = MemberFactory.create()
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=datetime.date(year=2025, month=1, day=1),
        )

        result = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=datetime.date(year=2025, month=1, day=1),
            cache={},
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.SEMIANNUALLY, result)

    def test_getMemberPaymentRhythm_memberHasARhythmObjectBeforeDate_returnsRhythmFromObject(
        self,
    ):
        member = MemberFactory.create()
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=datetime.date(year=2025, month=1, day=1),
        )

        result = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=datetime.date(year=2025, month=2, day=15),
            cache={},
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.SEMIANNUALLY, result)

    def test_getMemberPaymentRhythm_memberHasARhythmObjectAfterDate_returnsDefaultFromConfig(
        self,
    ):
        member = MemberFactory.create()
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=datetime.date(year=2025, month=3, day=1),
        )

        result = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=datetime.date(year=2025, month=2, day=15),
            cache={},
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.YEARLY, result)

    def test_getMemberPaymentRhythm_memberHasNoRhythmObject_returnsDefaultFromConfig(
        self,
    ):
        member = MemberFactory.create()
        self.assertEqual(0, MemberPaymentRhythm.objects.count())

        result = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=datetime.date(year=2025, month=2, day=15),
            cache={},
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.YEARLY, result)
