import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.services.subscription_update_view_change_applier import (
    SubscriptionUpdateViewChangeApplier,
)
from tapir.wirgarten.tests.test_utils import mock_timezone


@patch.object(
    MemberPaymentRhythmService, "assign_payment_rhythm_to_member", autospec=True
)
@patch.object(MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True)
@patch.object(
    MemberPaymentRhythmService,
    "get_date_of_next_payment_rhythm_change",
    autospec=True,
)
class TestChangePaymentRhythmIfNecessary(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=1865, month=3, day=27)
        )

    def test_changePaymentRhythmIfNecessary_paymentRhythmIsNone_doesNothing(
        self, *mocks
    ):
        SubscriptionUpdateViewChangeApplier.change_payment_rhythm_if_necessary(
            payment_rhythm=None,
            member=Mock(),
            actor=Mock(),
            cache=Mock(),
        )

        for mock in mocks:
            mock.assert_not_called()

    def test_changePaymentRhythmIfNecessary_rhythmAtNextChangeDateIsSameAsDesired_doesNothing(
        self,
        mock_get_date_of_next_payment_rhythm_change: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_assign_payment_rhythm_to_member: Mock,
    ):
        member = Mock()
        cache = Mock()
        date_of_next_rhythm_change = datetime.date(year=2028, month=1, day=1)
        mock_get_date_of_next_payment_rhythm_change.return_value = (
            date_of_next_rhythm_change
        )
        mock_get_member_payment_rhythm.return_value = "monthly"

        SubscriptionUpdateViewChangeApplier.change_payment_rhythm_if_necessary(
            payment_rhythm="monthly",
            member=member,
            actor=Mock(),
            cache=cache,
        )

        mock_get_date_of_next_payment_rhythm_change.assert_called_once_with(
            member=member,
            reference_date=self.now.date(),
            cache=cache,
        )
        mock_get_member_payment_rhythm.assert_called_once_with(
            member=member, reference_date=date_of_next_rhythm_change, cache=cache
        )
        mock_assign_payment_rhythm_to_member.assert_not_called()

    def test_changePaymentRhythmIfNecessary_rhythmAtNextChangeDateDiffersFromDesired_assignsNewRhythm(
        self,
        mock_get_date_of_next_payment_rhythm_change: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_assign_payment_rhythm_to_member: Mock,
    ):
        member = Mock()
        actor = Mock()
        cache = Mock()
        rhythm_valid_from = datetime.date(year=2028, month=1, day=1)
        mock_get_date_of_next_payment_rhythm_change.return_value = rhythm_valid_from
        mock_get_member_payment_rhythm.return_value = "monthly"

        SubscriptionUpdateViewChangeApplier.change_payment_rhythm_if_necessary(
            payment_rhythm="yearly",
            member=member,
            actor=actor,
            cache=cache,
        )

        mock_get_date_of_next_payment_rhythm_change.assert_called_once_with(
            member=member,
            reference_date=self.now.date(),
            cache=cache,
        )
        mock_get_member_payment_rhythm.assert_called_once_with(
            member=member, reference_date=rhythm_valid_from, cache=cache
        )
        mock_assign_payment_rhythm_to_member.assert_called_once_with(
            member=member,
            actor=actor,
            rhythm="yearly",
            valid_from=rhythm_valid_from,
            cache=cache,
        )
