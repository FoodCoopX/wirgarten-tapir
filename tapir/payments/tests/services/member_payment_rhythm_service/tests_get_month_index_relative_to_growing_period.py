import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestGetMonthIndexRelativeToGrowingPeriod(SimpleTestCase):
    @patch.object(TapirCache, "get_all_growing_periods_ascending")
    def test_getMonthIndexRelativeToGrowingPeriod_givenDateIsOnFirstMonth_returnsOne(
        self, mock_get_all_growing_periods_ascending: Mock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=7, day=1),
                end_date=datetime.date(year=2025, month=6, day=30),
            )
        ]
        cache = Mock()
        reference_date = datetime.date(year=2024, month=7, day=15)

        result = MemberPaymentRhythmService.get_month_index_relative_to_growing_period(
            reference_date=reference_date, cache=cache
        )

        self.assertEqual(1, result)
        mock_get_all_growing_periods_ascending.assert_called_once_with(cache=cache)

    @patch.object(TapirCache, "get_all_growing_periods_ascending")
    def test_getMonthIndexRelativeToGrowingPeriod_givenDateIsOnFifthMonth_returnsFive(
        self, mock_get_all_growing_periods_ascending: Mock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=1, day=1),
                end_date=datetime.date(year=2024, month=12, day=31),
            )
        ]
        cache = Mock()

        result = MemberPaymentRhythmService.get_month_index_relative_to_growing_period(
            reference_date=datetime.date(year=2024, month=5, day=30), cache=cache
        )

        self.assertEqual(5, result)
        mock_get_all_growing_periods_ascending.assert_called_once_with(cache=cache)

    @patch.object(TapirCache, "get_all_growing_periods_ascending")
    def test_getMonthIndexRelativeToGrowingPeriod_givenDateIsOnTwelfthMonth_returnsTwelve(
        self, mock_get_all_growing_periods_ascending: Mock
    ):
        mock_get_all_growing_periods_ascending.return_value = [
            GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=3, day=1),
                end_date=datetime.date(year=2025, month=2, day=28),
            )
        ]
        cache = Mock()

        result = MemberPaymentRhythmService.get_month_index_relative_to_growing_period(
            reference_date=datetime.date(year=2025, month=2, day=6), cache=cache
        )

        self.assertEqual(12, result)
        mock_get_all_growing_periods_ascending.assert_called_once_with(cache=cache)
