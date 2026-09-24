import datetime

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssignPaymentRhythmToMember(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM).update(
            value=MemberPaymentRhythm.Rhythm.MONTHLY
        )

    def test_assignPaymentRhythmToMember_cacheWarmedBeforeCreate_subsequentLookupSeesNewRhythm(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2026, month=9, day=21))
        member = MemberFactory.create()
        cache = {}
        reference_date = datetime.date(year=2026, month=9, day=21)

        MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=reference_date,
            cache=cache,
        )

        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
            valid_from=reference_date,
            cache=cache,
            actor=member,
        )

        result = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.QUARTERLY, result)
