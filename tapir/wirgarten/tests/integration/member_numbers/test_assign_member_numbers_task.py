from unittest.mock import patch

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tasks import assign_member_numbers
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssignMemberNumbersTask(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(ParameterKeys.ORGANISATION_LEGAL_STATUS, "ev")

    @staticmethod
    def _create_member_without_number() -> Member:
        member = MemberFactory.create()
        member.member_no = None
        member.save()
        return member

    def test_assignMemberNumbers_memberWithoutNumber_numberGetsAssignedAndMailTriggerIsFired(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        assign_member_numbers()

        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)

    def test_assignMemberNumbers_memberAlreadyHasNumber_memberNumberNotChangedAndMailTriggerNotFired(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=42)

        assign_member_numbers()

        member.refresh_from_db()
        self.assertEqual(42, member.member_no)

    @patch.object(
        MemberNumberService,
        "is_member_in_subscription_trial",
        autospec=True,
        return_value=True,
    )
    def test_assignMemberNumbers_trialToggleOffAndMemberInTrial_memberStaysWithoutNumber(
        self, _mock_is_member_in_subscription_trial
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        member = self._create_member_without_number()

        assign_member_numbers()

        member.refresh_from_db()
        self.assertIsNone(member.member_no)
