from django.core.management import call_command

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBackfillMemberNumbersCommand(TapirIntegrationTest):
    """
    Tests for the ``backfill_member_numbers`` management command, the one-off
    nudge introduced in US 4.3 (#535) to assign member numbers to members
    that existed before the immediate-assignment feature was deployed.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ASSIGN_DURING_TRIAL, True)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)

    @staticmethod
    def _set_parameter(key: str, value) -> None:
        TapirParameter.objects.filter(key=key).update(value=str(value))

    @staticmethod
    def _create_members_without_number(count: int) -> list[Member]:
        # ``MemberFactory.create(member_no=None)`` still auto-assigns via its
        # post_generation hook, so we have to null the field via raw UPDATE.
        members = [MemberFactory.create() for _ in range(count)]
        Member.objects.filter(pk__in=[m.pk for m in members]).update(member_no=None)
        for m in members:
            m.refresh_from_db()
        return members

    def test_backfillMemberNumbers_membersWithoutNumber_allGetNumbers(self):
        members = self._create_members_without_number(3)

        call_command("backfill_member_numbers")

        for member in members:
            member.refresh_from_db()
            self.assertIsNotNone(member.member_no)
        # Three distinct numbers were assigned.
        assigned = {Member.objects.get(pk=m.pk).member_no for m in members}
        self.assertEqual(3, len(assigned))

    def test_backfillMemberNumbers_dryRun_nothingChanges(self):
        members = self._create_members_without_number(2)

        call_command("backfill_member_numbers", "--dry-run")

        for member in members:
            member.refresh_from_db()
            self.assertIsNone(member.member_no)

    def test_backfillMemberNumbers_idempotent_runningTwiceIsSafe(self):
        members = self._create_members_without_number(2)

        call_command("backfill_member_numbers")
        first_run_numbers = {}
        for member in members:
            member.refresh_from_db()
            first_run_numbers[member.pk] = member.member_no
            self.assertIsNotNone(member.member_no)

        call_command("backfill_member_numbers")
        for member in members:
            member.refresh_from_db()
            # Running again must not overwrite existing numbers.
            self.assertEqual(first_run_numbers[member.pk], member.member_no)
