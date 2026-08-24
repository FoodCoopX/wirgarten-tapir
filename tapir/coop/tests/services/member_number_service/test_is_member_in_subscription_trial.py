from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager


class TestIsMemberInSubscriptionTrial(TapirUnitTest):
    @patch.object(
        TrialPeriodManager,
        "get_subscriptions_in_trial_period",
        autospec=True,
        return_value=["fake_sub"],
    )
    def test_isMemberInSubscriptionTrial_hasSubscriptionInTrial_returnsTrue(
        self, mock_get_subscriptions
    ):
        member = Mock()
        member.id = 7
        cache = {}

        self.assertTrue(
            MemberNumberService.is_member_in_subscription_trial(member, cache=cache)
        )
        mock_get_subscriptions.assert_called_once_with(member_id=7, cache=cache)

    @patch.object(
        TrialPeriodManager,
        "get_subscriptions_in_trial_period",
        autospec=True,
        return_value=[],
    )
    def test_isMemberInSubscriptionTrial_noSubscriptionInTrial_returnsFalse(
        self, mock_get_subscriptions
    ):
        member = Mock()
        member.id = 7
        cache = {}

        self.assertFalse(
            MemberNumberService.is_member_in_subscription_trial(member, cache=cache)
        )
        mock_get_subscriptions.assert_called_once_with(member_id=7, cache=cache)
