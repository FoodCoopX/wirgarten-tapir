from unittest.mock import patch

from tapir.configuration.models import TapirParameter
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberNumbersService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _set_parameter(key: str, value) -> None:
        TapirParameter.objects.filter(key=key).update(value=str(value))

    @staticmethod
    def _create_member_without_number() -> Member:
        member = MemberFactory.create()
        Member.objects.filter(pk=member.pk).update(member_no=None)
        member.refresh_from_db()
        return member

    # ------------------------------------------------------------------ #
    # format_member_no
    # ------------------------------------------------------------------ #

    def test_formatMemberNo_withPrefixAndPadding_returnsFormattedString(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)

        self.assertEqual("BT0017", MemberNumberService.format_member_no(17))

    def test_formatMemberNo_withoutPadding_returnsUnpaddedString(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 0)

        self.assertEqual("BT17", MemberNumberService.format_member_no(17))

    def test_formatMemberNo_withoutPrefix_returnsOnlyNumber(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)

        self.assertEqual("0017", MemberNumberService.format_member_no(17))

    def test_formatMemberNo_withNoneInput_returnsNone(self):
        self.assertIsNone(MemberNumberService.format_member_no(None))

    def test_formatMemberNo_numberLongerThanLength_returnsUntruncatedNumber(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 2)

        self.assertEqual("12345", MemberNumberService.format_member_no(12345))

    # ------------------------------------------------------------------ #
    # compute_next_member_no
    # ------------------------------------------------------------------ #

    def test_computeNextMemberNo_noExistingMembers_returnsStartValue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1000)
        self.assertFalse(Member.objects.exists())

        self.assertEqual(1000, MemberNumberService.compute_next_member_no())

    def test_computeNextMemberNo_existingMemberBelowStartValue_returnsStartValue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1000)
        MemberFactory.create(member_no=500)

        self.assertEqual(1000, MemberNumberService.compute_next_member_no())

    def test_computeNextMemberNo_existingMemberAboveStartValue_returnsMaxPlusOne(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        MemberFactory.create(member_no=42)

        self.assertEqual(43, MemberNumberService.compute_next_member_no())

    # ------------------------------------------------------------------ #
    # should_assign_member_no
    # ------------------------------------------------------------------ #

    def test_shouldAssignMemberNo_memberAlreadyHasNumber_returnsFalse(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=5)

        self.assertFalse(MemberNumberService.should_assign_member_no(member))

    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_onlyAfterTrialDisabledAndInTrial_returnsTrue(
        self, mock_is_in_coop_trial
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        mock_is_in_coop_trial.return_value = True
        member = self._create_member_without_number()

        self.assertTrue(MemberNumberService.should_assign_member_no(member))

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_onlyAfterTrialAndInCoopTrial_returnsFalse(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = True
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        self.assertFalse(MemberNumberService.should_assign_member_no(member))

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
    def test_shouldAssignMemberNo_onlyAfterTrialAndInSubTrial_returnsFalse(
        self,
        mock_is_in_coop_trial,
        mock_get_subscriptions_in_trial_period,
        _mock_legal_status,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = False
        mock_get_subscriptions_in_trial_period.return_value = ["fake_sub"]
        member = self._create_member_without_number()

        self.assertFalse(MemberNumberService.should_assign_member_no(member))

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_onlyAfterTrialAndNotInTrial_returnsTrue(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = False
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        self.assertTrue(MemberNumberService.should_assign_member_no(member))

    # ------------------------------------------------------------------ #
    # assign_member_no_if_eligible
    # ------------------------------------------------------------------ #

    def test_assignMemberNoIfEligible_eligible_assignsNumberAndReturnsTrue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        result = MemberNumberService.assign_member_no_if_eligible(member)

        self.assertTrue(result)
        self.assertIsNotNone(member.member_no)
        member.refresh_from_db()
        self.assertEqual(1, member.member_no)

    def test_assignMemberNoIfEligible_notEligible_doesNothingAndReturnsFalse(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=5)

        result = MemberNumberService.assign_member_no_if_eligible(member)

        self.assertFalse(result)
        member.refresh_from_db()
        self.assertEqual(5, member.member_no)

    def test_assignMemberNoIfEligible_respectsStartValue_usesStartValueAsLowerBound(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 500)
        member = self._create_member_without_number()

        result = MemberNumberService.assign_member_no_if_eligible(member)

        self.assertTrue(result)
        member.refresh_from_db()
        self.assertEqual(500, member.member_no)
