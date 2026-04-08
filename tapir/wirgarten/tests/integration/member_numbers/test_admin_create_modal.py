from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.member.list.modals import save_member_twice


class TestAdminCreateModalMemberNumber(TapirIntegrationTest):
    """
    Tests for the admin "create member" modal path.

    ``save_member_twice`` is called when an admin creates a member manually
    via the admin modal. Since US 4.3 (#535) it must assign a member
    number immediately — the member has no subscriptions or coop shares at
    this point, so the trial check reports "not in trial" and the number
    should be assigned.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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

    def test_saveMemberTwice_defaultSettings_memberGetsNumberImmediately(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        # Start from a member without a number; save_member_twice should
        # assign one immediately (there are no subscriptions/shares yet,
        # so the trial check reports "not in trial").
        member = self._create_member_without_number()

        save_member_twice(member)

        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)
