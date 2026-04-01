from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)


class TestIsStartOfRhythmPeriod(SimpleTestCase):
    @patch.object(
        MemberPaymentRhythmService, "get_month_index_relative_to_growing_period"
    )
    def test_isStartOfRhythmPeriod_indexOfGivenMonthIsInTheCreationMonthList_returnsTrue(
        self,
        mock_get_month_index_relative_to_growing_period: Mock,
    ):
        mock_get_month_index_relative_to_growing_period.return_value = 7
        rhythm = MemberPaymentRhythm.Rhythm.SEMIANNUALLY
        reference_date = Mock()
        cache = Mock()

        result = MemberPaymentRhythmService.is_start_of_rhythm_period(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        )

        self.assertTrue(result)
        mock_get_month_index_relative_to_growing_period.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )

    @patch.object(
        MemberPaymentRhythmService, "get_month_index_relative_to_growing_period"
    )
    def test_isStartOfRhythmPeriod_indexOfGivenMonthIsNotTheCreationMonthList_returnsTrue(
        self,
        mock_get_month_index_relative_to_growing_period: Mock,
    ):
        mock_get_month_index_relative_to_growing_period.return_value = 7
        rhythm = MemberPaymentRhythm.Rhythm.YEARLY
        reference_date = Mock()
        cache = Mock()

        result = MemberPaymentRhythmService.is_start_of_rhythm_period(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        )

        self.assertFalse(result)
        mock_get_month_index_relative_to_growing_period.assert_called_once_with(
            reference_date=reference_date, cache=cache
        )
