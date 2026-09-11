import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestJokerManagementServiceDoesMemberHaveAJokerInWeek(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value=True
        )

    def test_doesMemberHaveAJokerInWeek_noJokerInWeek_returnsFalse(self):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=3, day=2)
        )
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=3, day=10)
        )

        self.assertFalse(
            JokerManagementService.does_member_have_a_joker_in_week(
                member, datetime.date(year=2025, month=3, day=3), cache={}
            )
        )

    def test_doesMemberHaveAJokerInWeek_hasJokerInWeek_returnsTrue(self):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=3, day=6)
        )

        self.assertTrue(
            JokerManagementService.does_member_have_a_joker_in_week(
                member, datetime.date(year=2025, month=3, day=3), cache={}
            )
        )

    def test_doesMemberHaveAJokerInWeek_sameIsoWeekAcrossNewYear_returnsTrue(self):
        # 2026-12-31 and 2027-01-01 are both ISO week 53 of 2026, but their
        # calendar years differ. Comparing the ISO week against the calendar
        # year missed this and let the member receive a cancelled delivery.
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2027, month=1, day=1)
        )

        self.assertTrue(
            JokerManagementService.does_member_have_a_joker_in_week(
                member, datetime.date(year=2026, month=12, day=31), cache={}
            )
        )

    def test_doesMemberHaveAJokerInWeek_jokerBeforeNewYearReferenceAfter_returnsTrue(
        self,
    ):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2026, month=12, day=28)
        )

        self.assertTrue(
            JokerManagementService.does_member_have_a_joker_in_week(
                member, datetime.date(year=2027, month=1, day=3), cache={}
            )
        )

    def test_doesMemberHaveAJokerInWeek_adjacentIsoWeekAcrossNewYear_returnsFalse(self):
        # 2027-01-04 is ISO week 1 of 2027, the week after the joker.
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2026, month=12, day=31)
        )

        self.assertFalse(
            JokerManagementService.does_member_have_a_joker_in_week(
                member, datetime.date(year=2027, month=1, day=4), cache={}
            )
        )
