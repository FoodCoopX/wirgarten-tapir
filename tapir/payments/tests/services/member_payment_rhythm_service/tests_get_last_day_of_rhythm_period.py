import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestsGetLastDayOfRhythmPeriod(SimpleTestCase):
    @patch.object(TapirCache, "get_all_growing_periods_ascending")
    def test_getLastDayOfRhythmPeriod_givenDayIsLastDayOfRhythmPeriod_returnsSameDate(
        self, mock_get_all_growing_periods_ascending: Mock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=7, day=1),
                end_date=datetime.date(year=2025, month=6, day=30),
            )
        ]
        cache = Mock()

        result = MemberPaymentRhythmService.get_last_day_of_rhythm_period(
            rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
            reference_date=datetime.date(year=2025, month=4, day=30),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=4, day=30), result)
        mock_get_all_growing_periods_ascending.assert_called_once_with(cache=cache)

    @patch.object(TapirCache, "get_all_growing_periods_ascending")
    def test_getLastDayOfRhythmPeriod_givenDayIsFirstDayOfRhythmPeriod_returnsCorrectLastDay(
        self, mock_get_all_growing_periods_ascending: Mock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=7, day=1),
                end_date=datetime.date(year=2025, month=6, day=30),
            )
        ]
        cache = Mock()

        result = MemberPaymentRhythmService.get_last_day_of_rhythm_period(
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            reference_date=datetime.date(year=2025, month=1, day=1),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=6, day=30), result)
        mock_get_all_growing_periods_ascending.assert_has_calls(
            [
                call(
                    cache=cache,
                )
            ]
        )

    @patch.object(TapirCache, "get_all_growing_periods_ascending")
    def test_getLastDayOfRhythmPeriod_givenDayIsInTheMiddleOfRhythmPeriod_returnsCorrectLastDay(
        self, mock_get_all_growing_periods_ascending: Mock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=3, day=1),
                end_date=datetime.date(year=2025, month=2, day=28),
            )
        ]
        cache = Mock()

        result = MemberPaymentRhythmService.get_last_day_of_rhythm_period(
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            reference_date=datetime.date(year=2024, month=7, day=14),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2025, month=2, day=28), result)
        mock_get_all_growing_periods_ascending.assert_has_calls([call(cache=cache)])
