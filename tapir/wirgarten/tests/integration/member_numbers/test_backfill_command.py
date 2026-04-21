from django.core.management import call_command

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBackfillMemberNumbersCommand(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        cls._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)

    @staticmethod
    def _create_members_without_number(count: int) -> list[Member]:
        members = MemberFactory.create_batch(count)
        pks = [m.pk for m in members]
        Member.objects.filter(pk__in=pks).update(member_no=None)
        return list(Member.objects.filter(pk__in=pks))

    def test_backfillMemberNumbers_membersWithoutNumber_allGetNumbers(self):
        members = self._create_members_without_number(3)

        call_command("backfill_member_numbers")

        refreshed = {
            m.pk: m.member_no
            for m in Member.objects.filter(pk__in=[m.pk for m in members])
        }
        for pk, number in refreshed.items():
            self.assertIsNotNone(number, f"Member {pk} should have a number")
        self.assertEqual(3, len(set(refreshed.values())))

    def test_backfillMemberNumbers_dryRun_nothingChanges(self):
        members = self._create_members_without_number(2)

        call_command("backfill_member_numbers", "--dry-run")

        refreshed = Member.objects.filter(pk__in=[m.pk for m in members])
        for member in refreshed:
            self.assertIsNone(member.member_no)

    def test_backfillMemberNumbers_idempotent_runningTwiceIsSafe(self):
        members = self._create_members_without_number(2)

        call_command("backfill_member_numbers")
        first_run = {
            m.pk: m.member_no
            for m in Member.objects.filter(pk__in=[m.pk for m in members])
        }
        for number in first_run.values():
            self.assertIsNotNone(number)

        call_command("backfill_member_numbers")
        second_run = {
            m.pk: m.member_no
            for m in Member.objects.filter(pk__in=[m.pk for m in members])
        }
        self.assertEqual(first_run, second_run)
