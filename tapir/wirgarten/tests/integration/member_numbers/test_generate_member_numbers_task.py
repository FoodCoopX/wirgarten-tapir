from unittest.mock import patch

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tasks import generate_member_numbers
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGenerateMemberNumbersTask(TapirIntegrationTest):
    """
    Tests for the safety-net Celery task ``generate_member_numbers``.

    Since US 4.3 (#535) members receive their number immediately on creation;
    this task only catches members that slipped through (e.g. because the
    admin toggle suppressed assignment during their trial and their trial
    has now ended).
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        # The task fires a tapir_mail trigger on success — stub it out so
        # we don't depend on the mail module's configured segments.
        patcher_trigger = patch(
            "tapir.wirgarten.tasks.TransactionalTrigger.fire_action"
        )
        self.mock_fire_action = patcher_trigger.start()
        self.addCleanup(patcher_trigger.stop)

        # Default test-wirgarten instance runs as a cooperative. The task
        # skips members without a ``coop_entry_date`` in that case. Force
        # the non-cooperative branch so we can test the assignment logic
        # in isolation.
        patcher_legal_status = patch(
            "tapir.wirgarten.tasks.legal_status_is_cooperative",
            return_value=False,
        )
        patcher_legal_status.start()
        self.addCleanup(patcher_legal_status.stop)

    @staticmethod
    def _set_parameter(key: str, value) -> None:
        TapirParameter.objects.filter(key=key).update(value=str(value))

    @staticmethod
    def _create_member_without_number() -> Member:
        # ``MemberFactory.create(member_no=None)`` still auto-assigns via its
        # post_generation hook, so we have to null the field via raw UPDATE.
        member = MemberFactory.create()
        Member.objects.filter(pk=member.pk).update(member_no=None)
        member.refresh_from_db()
        return member

    def test_generateMemberNumbers_memberWithoutNumber_safetyNetAssignsNumber(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        generate_member_numbers(print_results=False)

        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)
        # MEMBERSHIP_ENTRY trigger is fired exclusively by the safety net.
        self.mock_fire_action.assert_called_once()

    def test_generateMemberNumbers_memberAlreadyHasNumber_isNotTouched(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=42)

        generate_member_numbers(print_results=False)

        member.refresh_from_db()
        self.assertEqual(42, member.member_no)
        # No eligible members -> trigger not fired.
        self.mock_fire_action.assert_not_called()

    @patch(
        "tapir.subscriptions.services.trial_period_manager."
        "TrialPeriodManager.get_subscriptions_in_trial_period"
    )
    @patch(
        "tapir.coop.services.membership_cancellation_manager."
        "MembershipCancellationManager.is_in_coop_trial"
    )
    def test_generateMemberNumbers_trialToggleOffAndMemberInTrial_memberStaysWithoutNumber(
        self, mock_is_in_coop_trial, mock_get_subscriptions_in_trial_period
    ):
        # Suppress assignment while the member is still in a trial period.
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        mock_is_in_coop_trial.return_value = True
        mock_get_subscriptions_in_trial_period.return_value = []
        member = self._create_member_without_number()

        generate_member_numbers(print_results=False)

        member.refresh_from_db()
        self.assertIsNone(member.member_no)
        self.mock_fire_action.assert_not_called()
