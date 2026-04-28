from unittest.mock import patch

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tasks import generate_member_numbers
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGenerateMemberNumbersTask(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        patcher_trigger = patch(
            "tapir.wirgarten.tasks.TransactionalTrigger.fire_action"
        )
        self.mock_fire_action = patcher_trigger.start()
        self.addCleanup(patcher_trigger.stop)

        self._set_parameter(ParameterKeys.ORGANISATION_LEGAL_STATUS, "ev")

    @staticmethod
    def _create_member_without_number() -> Member:
        member = MemberFactory.create()
        member.member_no = None
        member.save()
        return member

    def test_generateMemberNumbers_memberWithoutNumber_numberGetsAssignedAndMailTriggerIsFired(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        generate_member_numbers()

        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)
        self.mock_fire_action.assert_called_once()
        trigger_data = self.mock_fire_action.call_args_list[0].args[0]
        self.assertEqual(Events.MEMBERSHIP_ENTRY, trigger_data.key)
        self.assertEqual(member.id, trigger_data.recipient_id_in_base_queryset)

    def test_generateMemberNumbers_memberAlreadyHasNumber_memberNumberNotChangedAndMailTriggerNotFired(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=42)

        generate_member_numbers()

        member.refresh_from_db()
        self.assertEqual(42, member.member_no)
        self.mock_fire_action.assert_not_called()

    @patch.object(
        MemberNumberService,
        "is_member_in_subscription_trial",
        autospec=True,
        return_value=True,
    )
    def test_generateMemberNumbers_trialToggleOffAndMemberInTrial_memberStaysWithoutNumber(
        self, _mock_is_member_in_subscription_trial
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        member = self._create_member_without_number()

        generate_member_numbers()

        member.refresh_from_db()
        self.assertIsNone(member.member_no)
        self.mock_fire_action.assert_not_called()
