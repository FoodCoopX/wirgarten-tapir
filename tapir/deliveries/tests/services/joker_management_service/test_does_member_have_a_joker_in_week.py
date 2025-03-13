import datetime

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestJokerManagementServiceDoesMemberHaveAJokerInWeek(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

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
                member, datetime.date(year=2025, month=3, day=3)
            )
        )

    def test_doesMemberHaveAJokerInWeek_hasJokerInWeek_returnsTrue(self):
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=3, day=6)
        )

        self.assertTrue(
            JokerManagementService.does_member_have_a_joker_in_week(
                member, datetime.date(year=2025, month=3, day=3)
            )
        )
