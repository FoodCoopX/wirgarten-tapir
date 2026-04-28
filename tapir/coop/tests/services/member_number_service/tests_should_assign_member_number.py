from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestShouldAssignMemberNumber(SimpleTestCase):
    def test_shouldAssignMemberNumber_memberAlreadyHasNumber_returnsFalse(self):
        member = Mock()
        member.member_no = 5

        self.assertFalse(
            MemberNumberService.should_assign_member_number(member, cache={})
        )

    def test_shouldAssignMemberNumber_onlyAfterTrialDisabled_returnsTrue(self):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL,
            value=False,
        )
        member = Mock()
        member.member_no = None

        self.assertTrue(
            MemberNumberService.should_assign_member_number(member, cache=cache)
        )

    @patch(
        "tapir.coop.services.member_number_service.legal_status_is_cooperative",
        autospec=True,
        return_value=True,
    )
    @patch.object(
        MembershipCancellationManager,
        "is_in_coop_trial",
        autospec=True,
        return_value=True,
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndInCoopTrial_returnsFalse(
        self, mock_is_in_coop_trial, mock_legal_status
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL,
            value=True,
        )
        member = Mock()
        member.member_no = None

        self.assertFalse(
            MemberNumberService.should_assign_member_number(member, cache=cache)
        )
        mock_is_in_coop_trial.assert_called_once_with(member)
        mock_legal_status.assert_called_once_with(cache=cache)

    @patch(
        "tapir.coop.services.member_number_service.legal_status_is_cooperative",
        autospec=True,
        return_value=True,
    )
    @patch.object(
        MembershipCancellationManager,
        "is_in_coop_trial",
        autospec=True,
        return_value=False,
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndCoopTrialEnded_returnsTrue(
        self, mock_is_in_coop_trial, mock_legal_status
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL,
            value=True,
        )
        member = Mock()
        member.member_no = None

        self.assertTrue(
            MemberNumberService.should_assign_member_number(member, cache=cache)
        )
        mock_is_in_coop_trial.assert_called_once_with(member)
        mock_legal_status.assert_called_once_with(cache=cache)

    @patch(
        "tapir.coop.services.member_number_service.legal_status_is_cooperative",
        autospec=True,
        return_value=False,
    )
    @patch.object(
        MemberNumberService,
        "is_member_in_subscription_trial",
        autospec=True,
        return_value=True,
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndInSubscriptionTrial_returnsFalse(
        self, mock_is_in_subscription_trial, mock_legal_status
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL,
            value=True,
        )
        member = Mock()
        member.member_no = None

        self.assertFalse(
            MemberNumberService.should_assign_member_number(member, cache=cache)
        )
        mock_is_in_subscription_trial.assert_called_once_with(member, cache=cache)
        mock_legal_status.assert_called_once_with(cache=cache)

    @patch(
        "tapir.coop.services.member_number_service.legal_status_is_cooperative",
        autospec=True,
        return_value=False,
    )
    @patch.object(
        MemberNumberService,
        "is_member_in_subscription_trial",
        autospec=True,
        return_value=False,
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndSubscriptionTrialEnded_returnsTrue(
        self, mock_is_in_subscription_trial, mock_legal_status
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL,
            value=True,
        )
        member = Mock()
        member.member_no = None

        self.assertTrue(
            MemberNumberService.should_assign_member_number(member, cache=cache)
        )
        mock_is_in_subscription_trial.assert_called_once_with(member, cache=cache)
        mock_legal_status.assert_called_once_with(cache=cache)
