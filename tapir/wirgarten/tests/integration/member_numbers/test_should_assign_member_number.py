from unittest.mock import patch

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestShouldAssignMemberNumber(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _create_member_without_number() -> Member:
        member = MemberFactory.create()
        member.member_no = None
        member.save()
        return member

    def test_shouldAssignMemberNumber_memberAlreadyHasNumber_returnsFalse(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=5)

        self.assertFalse(
            MemberNumberService.should_assign_member_number(member, cache={})
        )

    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialDisabledAndInTrial_returnsTrue(
        self, mock_is_in_coop_trial
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        mock_is_in_coop_trial.return_value = True
        member = self._create_member_without_number()

        self.assertTrue(
            MemberNumberService.should_assign_member_number(member, cache={})
        )

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndInCoopTrial_returnsFalse(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = True
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        self.assertFalse(
            MemberNumberService.should_assign_member_number(member, cache={})
        )

    @patch(
        "tapir.coop.services.member_number_service.legal_status_is_cooperative",
        return_value=False,
    )
    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndInSubTrial_returnsFalse(
        self,
        mock_is_in_coop_trial,
        mock_get_subscriptions_in_trial_period,
        _mock_legal_status,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = False
        mock_get_subscriptions_in_trial_period.return_value = ["fake_sub"]
        member = self._create_member_without_number()

        self.assertFalse(
            MemberNumberService.should_assign_member_number(member, cache={})
        )

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNumber_onlyAfterTrialAndNotInTrial_returnsTrue(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = False
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        self.assertTrue(
            MemberNumberService.should_assign_member_number(member, cache={})
        )
