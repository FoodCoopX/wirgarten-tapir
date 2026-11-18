from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.core.exceptions import TapirImproperlyConfigured


class TestGetRhythmFromDisplayName(TapirUnitTest):
    def test_getRhythmFromDisplayName_exactDisplayName_returnsRhythm(self):
        result = MemberPaymentRhythmService.get_rhythm_from_display_name(
            display_name="Vierteljährlich"
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.QUARTERLY, result)

    def test_getRhythmFromDisplayName_differentCaseAndWhitespace_returnsRhythm(self):
        result = MemberPaymentRhythmService.get_rhythm_from_display_name(
            display_name=" halbjährlich "
        )

        self.assertEqual(MemberPaymentRhythm.Rhythm.SEMIANNUALLY, result)

    def test_getRhythmFromDisplayName_unknownDisplayName_raisesException(self):
        with self.assertRaises(TapirImproperlyConfigured):
            MemberPaymentRhythmService.get_rhythm_from_display_name(
                display_name="Wöchentlich"
            )
