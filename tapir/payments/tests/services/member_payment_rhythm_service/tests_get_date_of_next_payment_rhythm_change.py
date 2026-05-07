import datetime
from unittest.mock import patch, Mock

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetDateOfNextPaymentRhythmChange(TapirUnitTest):
    @patch.object(
        MemberPaymentRhythmService, "get_last_day_of_rhythm_period", autospec=True
    )
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MemberSolidarityContributionService, "get_member_contribution", autospec=True
    )
    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_getDateOfNextPaymentRhythmChange_memberHasASubscription_returnsDayAfterEndOfCurrentRhythm(
        self,
        mock_get_active_and_future_subscriptions_by_member_id: Mock,
        mock_get_member_contribution: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
    ):
        member = Mock(id="test_id")
        reference_date = Mock()
        mock_get_active_and_future_subscriptions_by_member_id.return_value = {
            "test_id": [Mock()]
        }
        mock_get_member_contribution.return_value = 0
        rhythm = Mock()
        mock_get_member_payment_rhythm.return_value = rhythm
        mock_get_last_day_of_rhythm_period.return_value = datetime.date(
            year=2017, month=9, day=30
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertEqual(datetime.date(year=2017, month=10, day=1), result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )
        mock_get_member_contribution.assert_called_once_with(
            member_id="test_id", reference_date=reference_date, cache=cache
        )
        mock_get_member_payment_rhythm.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        )

    @patch.object(
        MemberPaymentRhythmService, "get_last_day_of_rhythm_period", autospec=True
    )
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MemberSolidarityContributionService, "get_member_contribution", autospec=True
    )
    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_getDateOfNextPaymentRhythmChange_memberHasASolidarityContribution_returnsDayAfterEndOfCurrentRhythm(
        self,
        mock_get_active_and_future_subscriptions_by_member_id: Mock,
        mock_get_member_contribution: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
    ):
        member = Mock(id="test_id")
        reference_date = Mock()
        mock_get_active_and_future_subscriptions_by_member_id.return_value = {
            "test_id": []
        }
        mock_get_member_contribution.return_value = 12
        rhythm = Mock()
        mock_get_member_payment_rhythm.return_value = rhythm
        mock_get_last_day_of_rhythm_period.return_value = datetime.date(
            year=2017, month=9, day=30
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertEqual(datetime.date(year=2017, month=10, day=1), result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )
        mock_get_member_contribution.assert_called_once_with(
            member_id="test_id", reference_date=reference_date, cache=cache
        )
        mock_get_member_payment_rhythm.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        )

    @patch.object(
        MemberPaymentRhythmService, "get_last_day_of_rhythm_period", autospec=True
    )
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MemberSolidarityContributionService, "get_member_contribution", autospec=True
    )
    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_getDateOfNextPaymentRhythmChange_memberHasASubscriptionAndASolidarityContribution_returnsDayAfterEndOfCurrentRhythm(
        self,
        mock_get_active_and_future_subscriptions_by_member_id: Mock,
        mock_get_member_contribution: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
    ):
        member = Mock(id="test_id")
        reference_date = Mock()
        mock_get_active_and_future_subscriptions_by_member_id.return_value = {
            "test_id": [Mock()]
        }
        mock_get_member_contribution.return_value = 12
        rhythm = Mock()
        mock_get_member_payment_rhythm.return_value = rhythm
        mock_get_last_day_of_rhythm_period.return_value = datetime.date(
            year=2017, month=9, day=30
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertEqual(datetime.date(year=2017, month=10, day=1), result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )
        mock_get_member_contribution.assert_called_once_with(
            member_id="test_id", reference_date=reference_date, cache=cache
        )
        mock_get_member_payment_rhythm.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=reference_date, cache=cache
        )

    @patch.object(
        MemberPaymentRhythmService, "get_last_day_of_rhythm_period", autospec=True
    )
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MemberSolidarityContributionService, "get_member_contribution", autospec=True
    )
    @patch.object(
        TapirCache, "get_active_and_future_subscriptions_by_member_id", autospec=True
    )
    def test_getDateOfNextPaymentRhythmChange_memberHasNoSubscriptionAndNoSolidarityContribution_returnsReferenceDate(
        self,
        mock_get_active_and_future_subscriptions_by_member_id: Mock,
        mock_get_member_contribution: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
    ):
        member = Mock(id="test_id")
        reference_date = Mock()
        mock_get_active_and_future_subscriptions_by_member_id.return_value = {
            "test_id": []
        }
        mock_get_member_contribution.return_value = 0
        rhythm = Mock()
        mock_get_member_payment_rhythm.return_value = rhythm
        mock_get_last_day_of_rhythm_period.return_value = datetime.date(
            year=2017, month=9, day=30
        )
        cache = Mock()

        result = MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
            member=member, reference_date=reference_date, cache=cache
        )

        self.assertEqual(reference_date, result)

        mock_get_active_and_future_subscriptions_by_member_id.assert_called_once_with(
            cache=cache, reference_date=reference_date
        )
        mock_get_member_contribution.assert_called_once_with(
            member_id="test_id", reference_date=reference_date, cache=cache
        )
        mock_get_member_payment_rhythm.assert_not_called()
        mock_get_last_day_of_rhythm_period.assert_not_called()
