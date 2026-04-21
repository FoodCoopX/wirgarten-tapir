from unittest.mock import patch

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.member.list.modals import save_member_and_assign_number


class TestAdminCreateModalMemberNumber(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _create_member_without_number() -> Member:
        member = MemberFactory.create()
        Member.objects.filter(pk=member.pk).update(member_no=None)
        member.refresh_from_db()
        return member

    def test_createMemberAndAssignNumber_defaultSettings_memberGetsNumberImmediately(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        save_member_and_assign_number(member)

        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)

    @patch.object(
        MembershipCancellationManager,
        "is_in_coop_trial",
        autospec=True,
        return_value=True,
    )
    def test_createMemberAndAssignNumber_onlyAfterTrialEnabled_memberDoesNotGetNumber(
        self, _mock_is_in_coop_trial
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, True)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        save_member_and_assign_number(member)

        member.refresh_from_db()
        self.assertIsNone(member.member_no)
