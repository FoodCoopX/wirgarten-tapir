import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestsGetFirstDayOfRhythmPeriod(SimpleTestCase):
    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_getFirstDayOfRhythmPeriod_givenDayIsFirstDayOfRhythmPeriod_returnsSameDate(
        self, mock_get_growing_period_at_date: Mock
    ):
        mock_get_growing_period_at_date.return_value = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2024, month=7, day=1),
            end_date=datetime.date(year=2025, month=6, day=30),
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_first_day_of_rhythm_period(
            rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
            reference_date=datetime.date(year=2025, month=1, day=1),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=1, day=1), result)
        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=datetime.date(year=2025, month=1, day=1), cache=cache
        )

    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_getFirstDayOfRhythmPeriod_givenDayIsLastDayOfRhythmPeriod_returnsCorrectFirstDay(
        self, mock_get_growing_period_at_date: Mock
    ):
        mock_get_growing_period_at_date.return_value = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2024, month=7, day=1),
            end_date=datetime.date(year=2025, month=6, day=30),
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_first_day_of_rhythm_period(
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            reference_date=datetime.date(year=2024, month=12, day=31),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2024, month=7, day=1), result)
        mock_get_growing_period_at_date.assert_has_calls(
            [
                call(
                    reference_date=datetime.date(year=2024, month=12, day=1),
                    cache=cache,
                )
            ]
        )

    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_getFirstDayOfRhythmPeriod_givenDayIsInTheMiddleOfRhythmPeriod_returnsCorrectFirstDay(
        self, mock_get_growing_period_at_date: Mock
    ):
        mock_get_growing_period_at_date.return_value = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2024, month=3, day=1),
            end_date=datetime.date(year=2025, month=2, day=28),
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_first_day_of_rhythm_period(
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            reference_date=datetime.date(year=2024, month=7, day=14),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2024, month=3, day=1), result)
        mock_get_growing_period_at_date.assert_has_calls(
            [call(reference_date=datetime.date(year=2024, month=7, day=1), cache=cache)]
        )
