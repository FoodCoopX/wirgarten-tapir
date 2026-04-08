from unittest.mock import patch

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member_numbers import (
    assign_member_no_if_eligible,
    compute_next_member_no,
    format_member_no,
    should_assign_member_no,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberNumbersService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _set_parameter(key: str, value) -> None:
        # TapirParameter stores values as strings; cast to str to match.
        TapirParameter.objects.filter(key=key).update(value=str(value))

    @staticmethod
    def _create_member_without_number() -> Member:
        # ``MemberFactory.create(member_no=None)`` does NOT actually create a
        # member without a number — the post_generation hook treats None as
        # "no override" and still auto-assigns MAX+1. To get a truly
        # number-less member we have to null the field via a raw UPDATE
        # (which also skips ``Member.save`` and its Keycloak round-trip).
        member = MemberFactory.create()
        Member.objects.filter(pk=member.pk).update(member_no=None)
        member.refresh_from_db()
        return member

    # ------------------------------------------------------------------ #
    # format_member_no
    # ------------------------------------------------------------------ #

    def test_formatMemberNo_withPrefixAndPadding_returnsFormattedString(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_LENGTH, 4)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD, True)

        self.assertEqual("BT0017", format_member_no(17))

    def test_formatMemberNo_withoutPadding_returnsUnpaddedString(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_LENGTH, 4)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD, False)

        self.assertEqual("BT17", format_member_no(17))

    def test_formatMemberNo_withoutPrefix_returnsOnlyNumber(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_LENGTH, 4)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD, True)

        self.assertEqual("0017", format_member_no(17))

    def test_formatMemberNo_withNoneInput_returnsNone(self):
        self.assertIsNone(format_member_no(None))

    def test_formatMemberNo_numberLongerThanLength_returnsUntruncatedNumber(self):
        # Python f-string 0-padding is a minimum width, not a maximum — so a
        # number longer than the configured length is returned unchanged.
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_LENGTH, 2)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD, True)

        self.assertEqual("12345", format_member_no(12345))

    # ------------------------------------------------------------------ #
    # compute_next_member_no
    # ------------------------------------------------------------------ #

    def test_computeNextMemberNo_noExistingMembers_returnsStartValue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1000)
        self.assertFalse(Member.objects.exists())

        self.assertEqual(1000, compute_next_member_no())

    def test_computeNextMemberNo_existingMemberBelowStartValue_returnsStartValue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1000)
        MemberFactory.create(member_no=500)

        self.assertEqual(1000, compute_next_member_no())

    def test_computeNextMemberNo_existingMemberAboveStartValue_returnsMaxPlusOne(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        MemberFactory.create(member_no=42)

        self.assertEqual(43, compute_next_member_no())

    # ------------------------------------------------------------------ #
    # should_assign_member_no
    # ------------------------------------------------------------------ #

    def test_shouldAssignMemberNo_memberAlreadyHasNumber_returnsFalse(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        member = MemberFactory.create(member_no=5)

        self.assertFalse(should_assign_member_no(member))

    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_trialAllowedAndInTrial_returnsTrue(
        self, mock_is_in_coop_trial
    ):
        # Toggle is on -> trial state does not matter, must return True.
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        mock_is_in_coop_trial.return_value = True
        member = self._create_member_without_number()

        self.assertTrue(should_assign_member_no(member))

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_trialNotAllowedAndInCoopTrial_returnsFalse(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, False)
        mock_is_in_coop_trial.return_value = True
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        self.assertFalse(should_assign_member_no(member))

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_trialNotAllowedAndInSubTrial_returnsFalse(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, False)
        mock_is_in_coop_trial.return_value = False
        # A non-empty list is enough — the service only checks ``len() > 0``.
        mock_get_subscriptions_in_trial_period.return_value = ["fake_sub"]
        member = self._create_member_without_number()

        self.assertFalse(should_assign_member_no(member))

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_shouldAssignMemberNo_trialNotAllowedAndNotInTrial_returnsTrue(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, False)
        mock_is_in_coop_trial.return_value = False
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        self.assertTrue(should_assign_member_no(member))

    # ------------------------------------------------------------------ #
    # assign_member_no_if_eligible
    # ------------------------------------------------------------------ #

    def test_assignMemberNoIfEligible_eligible_assignsNumberAndReturnsTrue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        result = assign_member_no_if_eligible(member)

        self.assertTrue(result)
        self.assertIsNotNone(member.member_no)
        # Persistence sanity check — reload from DB.
        member.refresh_from_db()
        self.assertEqual(1, member.member_no)

    def test_assignMemberNoIfEligible_notEligible_doesNothingAndReturnsFalse(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        member = MemberFactory.create(member_no=5)

        result = assign_member_no_if_eligible(member)

        self.assertFalse(result)
        member.refresh_from_db()
        self.assertEqual(5, member.member_no)

    def test_assignMemberNoIfEligible_respectsStartValue_usesStartValueAsLowerBound(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 500)
        member = self._create_member_without_number()

        result = assign_member_no_if_eligible(member)

        self.assertTrue(result)
        member.refresh_from_db()
        self.assertEqual(500, member.member_no)
